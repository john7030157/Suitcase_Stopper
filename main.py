import cv2
import time
import math
import numpy as np
from ultralytics import YOLO

# 분리한 모듈 임포트
import config as cfg
from camera_engine import CamStream, RailMapper
from motor_control import MotorController

def nothing(x): pass

def run_system():
    # 1. 초기화
    print(f"[System] 모드: {cfg.SYSTEM_MODE} 시작")
    
    # 객체 생성
    motor = MotorController()
    mapper = RailMapper()
    cam_mtx, cam_dist = mapper.load_lens_calibration()
    
    print(f"[System] YOLO 모델 로딩 중... ({cfg.MODEL_PATH})")
    model = YOLO(cfg.MODEL_PATH)
    
    # 카메라 시작
    cam_stream = CamStream(src=cfg.CAM_INDEX).start()
    
    # 렌즈 왜곡 보정 맵 생성
    new_cam_mtx, mapx, mapy = None, None, None
    if cam_mtx is not None:
        temp = cam_stream.read()
        while temp is None: temp = cam_stream.read()
        h, w = temp.shape[:2]
        new_cam_mtx, _ = cv2.getOptimalNewCameraMatrix(cam_mtx, cam_dist, (w,h), 1, (w,h))
        mapx, mapy = cv2.initUndistortRectifyMap(cam_mtx, cam_dist, None, new_cam_mtx, (w,h), 5)

    # 2. 캘리브레이션 실행
    if not mapper.perform_calibration(cam_stream, cam_mtx, cam_dist, new_cam_mtx):
        print("[System] 종료")
        cam_stream.stop()
        return

    # ArUco 설정
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(aruco_dict, cv2.aruco.DetectorParameters())

    # 튜닝 윈도우 생성
    cv2.namedWindow("Control", cv2.WINDOW_NORMAL)
    cv2.createTrackbar('Exposure', "Control", 20, 20, nothing) 
    cv2.createTrackbar('Gain', "Control", 100, 200, nothing)
    
    # 상태 변수들
    track_history = {}
    smooth_pos = {}
    is_fall_active = False
    consecutive_trigger = 0
    last_act_time = 0
    target_rail_pos = None
    last_known_pos = None
    last_marker_time = 0
    
    print("[System] 루프 진입")
    
    try:
        while True:
            # A. 영상 획득 및 전처리
            frame = cam_stream.read()
            if frame is None: continue
            
            curr_time = time.time()
            if mapx is not None:
                frame = cv2.remap(frame, mapx, mapy, cv2.INTER_LINEAR)
                
            # 카메라 파라미터 조절
            exp = cv2.getTrackbarPos('Exposure', "Control")
            gain = cv2.getTrackbarPos('Gain', "Control")
            cam_stream.stream.set(cv2.CAP_PROP_EXPOSURE, exp - 13)
            cam_stream.stream.set(cv2.CAP_PROP_GAIN, gain)

            # B. ArUco (내 위치)
            corners, ids, _ = detector.detectMarkers(frame)
            my_pos_pct = None
            
            if ids is not None:
                ids = ids.flatten()
                for i, mid in enumerate(ids):
                    if mid == 0: # DEVICE_MARKER_ID
                        c = corners[i][0]
                        cx, cy = int(np.mean(c[:, 0])), int(np.mean(c[:, 1]))
                        cv2.aruco.drawDetectedMarkers(frame, corners)
                        
                        my_pos_pct = mapper.transform_point((cx, cy))
                        last_known_pos = my_pos_pct
                        last_marker_time = curr_time
                        cv2.putText(frame, f"Me:{my_pos_pct:.1f}%", (cx, cy-20), 0, 0.5, (0,255,255), 2)
                        break

            # C. YOLO (목표물)
            results = model.track(frame, persist=True, classes=[0, 1], verbose=False, conf=0.35)
            high_speed_detected = False
            curr_carrier_pos = None

            if results[0].boxes.id is not None:
                for tid, box, cls in zip(results[0].boxes.id.int().tolist(), results[0].boxes.xyxy.cpu(), results[0].boxes.cls.tolist()):
                    x1, y1, x2, y2 = map(int, box.tolist())
                    cx, cy = (x1+x2)//2, (y1+y2)//2
                    
                    if mapper.rail_contour is not None:
                        if cv2.pointPolygonTest(mapper.rail_contour, (cx, cy), False) < 0: continue

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0,0,255), 2)
                    
                    if int(cls) == 0: # Carrier
                        # 스무딩
                        if tid in smooth_pos:
                            sx = int(cx * cfg.SMOOTHING_FACTOR + smooth_pos[tid][0] * (1-cfg.SMOOTHING_FACTOR))
                            sy = int(cy * cfg.SMOOTHING_FACTOR + smooth_pos[tid][1] * (1-cfg.SMOOTHING_FACTOR))
                        else: sx, sy = cx, cy
                        smooth_pos[tid] = (sx, sy)
                        
                        # 속도 계산
                        track_history.setdefault(tid, []).append((sx, sy, curr_time))
                        hist = track_history[tid]
                        if len(hist) > 30: hist.pop(0)
                        
                        speed = 0.0
                        if len(hist) >= 3:
                            (lx, ly, lt), _, (fx, fy, ft) = hist[-1], hist[-2], hist[-3]
                            dt = lt - ft
                            if dt > 0.001:
                                speed = math.sqrt(((lx-fx)/dt)**2 + ((ly-fy)/dt)**2)
                        
                        curr_pct = mapper.transform_point((sx, sy))
                        
                        # 낙하 판단
                        falling = False
                        if len(hist) >= 3:
                            past_pct = mapper.transform_point(hist[-3][:2])
                            falling = (curr_pct - past_pct) > 0.5
                            
                        if speed > cfg.INIT_VEL_THRESH and falling:
                            high_speed_detected = True
                            curr_carrier_pos = curr_pct
                        
                        cv2.putText(frame, f"V:{int(speed)}", (x1, y1-20), 0, 0.5, (0,255,255), 2)

            # D. 로직 판단 (FSM)
            if high_speed_detected: consecutive_trigger += 1
            else: consecutive_trigger = 0
            
            if consecutive_trigger >= cfg.INIT_TRIG_FRAMES:
                is_fall_active = True
                last_act_time = curr_time
                if curr_carrier_pos:
                    # 설정된 오프셋 적용
                    target_rail_pos = min(100.0, curr_carrier_pos + cfg.BLOCKING_OFFSET)

            # 쿨다운 체크
            if is_fall_active and (curr_time - last_act_time > cfg.INIT_COOLDOWN):
                if not high_speed_detected: is_fall_active = False

            # E. 모터 제어
            final_cmd = 0
            if is_fall_active:
                cv2.putText(frame, "!!! FALL DETECTED !!!", (300, 200), 0, 1.5, (0,0,255), 3)
                
                ctrl_pos = my_pos_pct
                if ctrl_pos is None and (curr_time - last_marker_time < 0.5):
                    ctrl_pos = last_known_pos # 메모리 추적
                
                if ctrl_pos is not None and target_rail_pos is not None:
                    raw_cmd, error = motor.calculate_pid_command(target_rail_pos, ctrl_pos)
                    
                    # [Catching 모드 전용 로직] 777 명령
                    if cfg.SYSTEM_MODE == 'CATCHING' and cfg.ENABLE_EMERGENCY_DROP:
                        if raw_cmd < cfg.EMERGENCY_DROP_SPEED: # 특정 속도 미만이면
                            final_cmd = 777
                            cv2.putText(frame, "DROP SHIELD (777)", (300, 400), 0, 1.5, (0,0,255), 4)
                        else:
                            final_cmd = raw_cmd
                    else:
                        final_cmd = raw_cmd
                        
                    cv2.putText(frame, f"T:{target_rail_pos:.0f} M:{ctrl_pos:.0f} E:{error:.1f}", (200, 50), 0, 0.6, (0,255,255), 2)
            else:
                motor.last_error = 0 # 리셋
            
            motor.send_command(final_cmd)
            
            # F. 화면 표시 및 키 입력
            if mapper.rail_contour is not None:
                cv2.polylines(frame, [mapper.rail_contour], True, (255,0,0), 2)
            
            cv2.imshow("Main View", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                motor.emergency_reset()
                is_fall_active = False

    finally:
        motor.close()
        cam_stream.stop()
        cv2.destroyAllWindows()
        print("[System] 종료됨")

if __name__ == "__main__":
    run_system()