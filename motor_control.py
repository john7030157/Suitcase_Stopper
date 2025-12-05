import serial
import time
import config as cfg

class MotorController:
    def __init__(self):
        self.ser = None
        try:
            self.ser = serial.Serial(cfg.SERIAL_PORT, cfg.BAUD_RATE, timeout=1)
            time.sleep(2)
            print(f"[Motor] 아두이노 연결 성공: {cfg.SERIAL_PORT}")
        except:
            print("[Motor] 아두이노 연결 실패 (가상 모드)")
        
        self.last_error = 0.0

    def send_command(self, cmd):
        if self.ser:
            try:
                msg = str(cmd) + '\n'
                self.ser.write(msg.encode())
            except Exception as e:
                print(f"[Motor Error] {e}")

    def read_msg(self):
        if self.ser and self.ser.in_waiting > 0:
            return self.ser.readline().decode().strip()
        return None

    def calculate_pid_command(self, target_pos, current_pos):
        """PID 계산 후 모터 명령 반환"""
        error = current_pos - target_pos
        d_error = error - self.last_error
        
        # config.py의 상수 사용
        pd_value = (error * cfg.INIT_Kp) + (d_error * cfg.INIT_Kd)
        self.last_error = error
        
        cmd = int(pd_value)
        
        # 방향 및 속도 제한
        if cmd > 0: # 상승
            cmd = min(cmd, cfg.MAX_SPEED_UP)
        else:       # 하강
            cmd = max(cmd, -cfg.MAX_SPEED_DOWN)
            
        # 최소 기동 전압 보정
        if 0 < abs(cmd) < 5:
            cmd = 5 * (1 if cmd > 0 else -1)
            
        return cmd, error

    def emergency_reset(self):
        print("[Motor] 리셋 명령(888) 전송")
        self.send_command(888)
        self.last_error = 0

    def close(self):
        if self.ser:
            self.send_command(0)
            self.ser.close()