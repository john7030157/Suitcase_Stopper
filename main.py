import cv2
import time
import math
import numpy as np
from ultralytics import YOLO

import config as cfg
from camera_engine import CamStream, RailMapper
from motor_control import MotorController

def nothing(x): pass

def run_system():
    # 1. 초기화
    print(f"[System] 현재 모드: {cfg.SYSTEM_MODE}")
    motor = MotorController()
    mapper = RailMapper()
    cam_mtx, cam_dist = mapper.load_lens_calibration()
    
    print(f"[System] YOLO 모델 로딩...")
    model = YOLO(cfg.MODEL_PATH)
    cam_stream = CamStream(src=cfg.CAM_INDEX).start()
    
    # 렌즈 보정 맵 생성
    new_cam_mtx, mapx, mapy = None, None, None
    if cam_mtx is not None:
        temp = cam_stream.read()
        while temp is None: temp = cam_stream.read()
        h, w = temp.shape[:2]
        new_cam_mtx, roi = cv2.getOptimalNewCameraMatrix(cam_mtx, cam_dist, (w,h), 1, (w,h))
        mapx, mapy = cv2.initUndistortRectifyMap(cam_mtx, cam_dist, None, new_cam_mtx, (w,h), 5)

    # 캘리브레이션 (화면 좌표계 설정)
    if not mapper.perform_calibration(cam_stream, cam_mtx, cam_dist, new_cam_mtx):
        cam_stream.stop()
        return

    # ---------------------------------------------------------
    # [2] 초기 호밍 (Homing) - 센서 원점 잡기
    # ---------------------------------------------------------
    print("=========================================")
    print(" [초기화] 아두이노 호밍(Homing) 시작...")
    print("=========================================")
    motor.start_homing()
    
    homing_done = False
    start_wait = time.time()
    while time.time() - start_wait < cfg.HOMING_TIMEOUT:
        status = motor.read_status()
        if status == "HOMED":
            print("[System] 호밍 완료! (Arduino: HOMED)")
            homing_done = True
            break
        # 화면이 멈추지 않게 업데이트
        frame = cam_stream.read()
        if frame is not None: cv2.imshow("Main View", frame)
        if cv2.waitKey(10) & 0xFF == ord('q'): return

    if not homing_done:
        print("[Warning] 호밍 응답 없음. (강제 진행)")

    # ---------------------------------------------------------
    # [3] 메인 루프
    # ---------------------------------------------------------
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(aruco_dict, cv2.aruco.DetectorParameters())
    
    # 변수 초기화
    track_history = {}
    smooth_pos = {}
    
    # 상태 관리 변수
    catching_state = "IDLE"   # Catching 모드용 상태 (IDLE -> DROPPING -> DEPLOYED)
    pid_active = False        # Tracking 모드용 활성화 플래그
    consecutive_trigger = 0
    
    # 제어용 변수
    last_known_my_pos = None  # 마커 놓쳤을 때 대비
    last_act_time = 0         # PID 쿨다운용

    try:
        while True:
            frame = cam_stream.read()
            if frame is None: continue
            
            curr_time = time.time()
            if mapx is not None: frame = cv2.remap(frame, mapx, mapy, cv2.INTER_LINEAR)

            # 아두이노 센서 상태 수신 (중요!)
            hw_status = motor.read_status()

            # -------------------------------------
            # A. 내 위치 파악 (ArUco) - 공통
            # -------------------------------------
            my_pos_pct = None
            corners, ids, _ = detector.detectMarkers(frame)
            if ids is not None:
                ids = ids.flatten()
                for i, mid in enumerate(ids):
                    if mid == 0:
                        c = corners[i][0]
                        cx, cy = int(np.mean(c[:, 0])), int(np.mean(c[:, 1]))
                        cv2.aruco.drawDetectedMarkers(frame, corners)
                        my_pos_pct = mapper.transform_point((cx, cy))
                        last_known_my_pos = my_pos_pct
                        cv2.putText(frame, f"Me:{my_pos_pct:.1f}%", (cx, cy-20), 0, 0.5, (0,255,255), 2)
                        break
            
            if my_pos_pct is None: my_pos_pct = last_known_my_pos # 메모리 사용

            # -------------------------------------
            # B. 목표물 감지 (YOLO) - 공통
            # -------------------------------------
            results = model.track(frame, persist=True, classes=[0], verbose=False, conf=0.35)
            
            fall_detected = False
            curr_carrier_pos = None

            if results[0].boxes.id is not None:
                for tid, box in zip(results[0].boxes.id.int().tolist(), results[0].boxes.xyxy.cpu()):
                    x1, y1, x2, y2 = map(int, box.tolist())
                    cx, cy = (x1+x2)//2, (y1+y2)//2
                    
                    # 스무딩 & 속도 계산
                    if tid not in smooth_pos: smooth_pos[tid] = (cx, cy)
                    sx = int(cx * cfg.SMOOTHING_FACTOR + smooth_pos[tid][0] * (1-cfg.SMOOTHING_FACTOR))
                    sy = int(cy * cfg.SMOOTHING_FACTOR + smooth_pos[tid][1] * (1-cfg.SMOOTHING_FACTOR))
                    smooth_pos[tid] = (sx, sy)
                    
                    track_history.setdefault(tid, []).append((sx, sy, curr_time))
                    if len(track_history[tid]) > 20: track_history[tid].pop(0)
                    
                    # 속도 판단
                    speed = 0.0
                    hist = track_history[tid]
                    is_downward = False
                    
                    if len(hist) >= 4:
                        (lx, ly, lt), (fx, fy, ft) = hist[-1], hist[-4]
                        dt = lt - ft
                        if dt > 0.01:
                            vy = (ly - fy) / dt
                            speed = abs(vy)
                            if vy > 0: is_downward = True # 화면 아래로 이동 (추락)

                    # 감지 로직
                    if speed > cfg.INIT_VEL_THRESH and is_downward:
                        fall_detected = True
                        curr_carrier_pos = mapper.transform_point((sx, sy))
                    
                    color = (0,0,255) if fall_detected else (255,0,0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"V:{int(speed)}", (x1, y1-10), 0, 0.6, color, 2)

            # 트리거 카운터
            if fall_detected: consecutive_trigger += 1
            else: consecutive_trigger = 0
            is_triggered = (consecutive_trigger >= cfg.INIT_TRIG_FRAMES)


            # =========================================================
            # C. 제어 로직 분기 (핵심 수정 부분)
            # =========================================================
            
            motor_cmd = 0

            # [CASE 1] CATCHING 모드 (급강하 -> 센서 디플로이)
            if cfg.SYSTEM_MODE == 'CATCHING':
                
                if catching_state == "IDLE":
                    if is_triggered:
                        print("[Catching] 낙하 감지! 급강하 시작!")
                        catching_state = "DROPPING"
                        
                elif catching_state == "DROPPING":
                    # 하강 중 센서 감지 체크
                    if hw_status == "BOTTOM_HIT":
                        print("[Catching] 바닥 센서 감지! 디플로이 전개!")
                        motor.deploy_shield() # 777 전송
                        catching_state = "DEPLOYED"
                    else:
                        motor.emergency_drop() # -255 전송 (계속 하강)
                        cv2.putText(frame, "!!! DROPPING !!!", (300, 300), 0, 2, (0,0,255), 4)

                elif catching_state == "DEPLOYED":
                    cv2.putText(frame, "SHIELD DEPLOYED", (300, 300), 0, 2, (0,255,0), 4)
                    # 동작 완료 상태, 명령 없음 (0)

            # [CASE 2] TRACKING 모드 (PID 제어)
            else: 
                # 활성화 조건 체크
                if is_triggered:
                    pid_active = True
                    last_act_time = curr_time
                
                # 쿨다운 체크
                if pid_active and (curr_time - last_act_time > cfg.INIT_COOLDOWN):
                    if not fall_detected: pid_active = False

                if pid_active and curr_carrier_pos is not None and my_pos_pct is not None:
                    # 목표 위치 설정 (오프셋 포함)
                    target = min(100.0, curr_carrier_pos + cfg.BLOCKING_OFFSET)
                    
                    # PID 계산
                    cmd, err = motor.calculate_pid_command(target, my_pos_pct)
                    motor_cmd = cmd
                    
                    cv2.putText(frame, f"PID Active | Err:{err:.1f}", (200, 50), 0, 0.7, (0,255,255), 2)
                
                # Tracking 모드여도 0이면 전송
                if cfg.SYSTEM_MODE == 'TRACKING':
                    motor.send_command(motor_cmd)

            # 화면 갱신
            if mapper.rail_contour is not None:
                cv2.polylines(frame, [mapper.rail_contour], True, (255,0,0), 2)
            cv2.imshow("Main View", frame)

            # 키 입력
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'): # 리셋
                print("[System] 리셋 요청 -> 호밍 재실행")
                catching_state = "IDLE"
                pid_active = False
                motor.start_homing()

    finally:
        motor.close()
        cam_stream.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    run_system()