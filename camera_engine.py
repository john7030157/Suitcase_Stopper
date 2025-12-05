import cv2
import time
import numpy as np
import json
import os
from threading import Thread
import config as cfg

class CamStream:
    """oCam 고속 영상 획득 클래스"""
    def __init__(self, src=0, width=1280, height=800):
        params = [cv2.CAP_PROP_CONVERT_RGB, 0, cv2.CAP_PROP_MODE, 0]
        self.stream = cv2.VideoCapture(src, cv2.CAP_MSMF, params)
        self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'GRBG'))
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.stream.set(cv2.CAP_PROP_FPS, 60)
        self.width = int(self.stream.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        (self.grabbed, self.raw_frame) = self.stream.read()
        self.latest_frame = None
        self.stopped = False
        print(f"[CamEngine] 카메라 초기화: {self.width}x{self.height}")

    def start(self):
        Thread(target=self.update, args=(), daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            (grabbed, raw) = self.stream.read()
            if not grabbed:
                self.stopped = True
                continue
            self.latest_frame = self.process_raw(raw)

    def process_raw(self, raw_frame):
        if len(raw_frame.shape) == 2 and raw_frame.shape[0] == 1:
            frame_2d = raw_frame.reshape(self.height, self.width)
        else:
            frame_2d = raw_frame
        try:
            return cv2.cvtColor(frame_2d, cv2.COLOR_BAYER_GB2BGR)
        except:
            return frame_2d

    def read(self):
        return self.latest_frame

    def stop(self):
        self.stopped = True
        self.stream.release()

class RailMapper:
    """좌표 변환 및 캘리브레이션 관리"""
    def __init__(self):
        self.calib_points = []
        self.perspective_matrix = None
        self.rail_contour = None
        self.calibration_scale = 1.0
        self.rail_length_px = 640 

    def load_lens_calibration(self):
        if os.path.exists(cfg.CALIB_FILE):
            with open(cfg.CALIB_FILE, 'r') as f:
                data = json.load(f)
            return np.array(data["camera_matrix"]), np.array(data["dist_coeffs"])
        return None, None

    def transform_point(self, point):
        """화면 좌표(px) -> 레일 진행률(%)"""
        if self.perspective_matrix is None: return 0
        src = np.array([[[point[0], point[1]]]], dtype=np.float32)
        dst = cv2.perspectiveTransform(src, self.perspective_matrix)
        linear_x = dst[0][0][0]
        return max(0, min(100, (linear_x / self.rail_length_px) * 100))

    def _mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(self.calib_points) < 4:
            real_x = int(x / self.calibration_scale)
            real_y = int(y / self.calibration_scale)
            self.calib_points.append((real_x, real_y))
            print(f"[Calibration] Point {len(self.calib_points)}: ({real_x},{real_y})")

    def perform_calibration(self, cam_stream, mtx=None, dist=None, new_cam_mtx=None):
        print("[System] 캘리브레이션 시작 (4점을 찍으세요)")
        time.sleep(1.0)
        
        frame = cam_stream.read()
        while frame is None:
            frame = cam_stream.read()
            time.sleep(0.1)

        if mtx is not None:
            frame = cv2.undistort(frame, mtx, dist, None, new_cam_mtx)

        actual_w = frame.shape[1]
        target_disp = 960.0
        self.calibration_scale = target_disp / actual_w if actual_w > target_disp else 1.0
        
        window_name = "Calibration"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self._mouse_callback)
        
        while True:
            disp = frame.copy()
            for i, pt in enumerate(self.calib_points):
                cv2.circle(disp, pt, 5, (0, 0, 255), -1)
                cv2.putText(disp, str(i+1), (pt[0]+10, pt[1]), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

            if len(self.calib_points) == 4:
                cv2.polylines(disp, [np.array(self.calib_points)], True, (0, 255, 0), 2)
                cv2.putText(disp, "Press ANY KEY to Apply", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

            show_frame = cv2.resize(disp, (0,0), fx=self.calibration_scale, fy=self.calibration_scale)
            cv2.imshow(window_name, show_frame)
            
            key = cv2.waitKey(20) & 0xFF
            if len(self.calib_points) == 4 and key != 255: break
            if key == ord('q'): return False

        cv2.destroyWindow(window_name)
        
        src_pts = np.float32(self.calib_points)
        dst_pts = np.float32([[0, 0], [self.rail_length_px, 0], [self.rail_length_px, 100], [0, 100]])
        self.perspective_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        self.rail_contour = np.array(self.calib_points, dtype=np.int32)
        return True