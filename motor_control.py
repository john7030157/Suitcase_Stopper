import serial
import time
import config as cfg

class MotorController:
    def __init__(self):
        self.ser = None
        try:
            # 타임아웃을 짧게 주어 메인 루프가 멈추지 않게 함
            self.ser = serial.Serial(cfg.SERIAL_PORT, cfg.BAUD_RATE, timeout=0.05)
            time.sleep(2)
            print(f"[Motor] 아두이노 연결 성공: {cfg.SERIAL_PORT}")
        except:
            print("[Motor] 아두이노 연결 실패 (가상 모드)")
        
        self.last_error = 0.0

    def send_command(self, cmd):
        if self.ser:
            try:
                msg = f"{int(cmd)}\n"
                self.ser.write(msg.encode())
            except Exception as e:
                print(f"[TX Error] {e}")

    def read_status(self):
        """
        아두이노로부터 메시지 수신 (센서 감지 여부)
        - 리턴값: "HOMED", "BOTTOM_HIT", "TOP_HIT" 등
        """
        if self.ser and self.ser.in_waiting > 0:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line: return line
            except: pass
        return None

    def calculate_pid_command(self, target_pos, current_pos):
        """Tracking 모드용 PID 계산"""
        error = current_pos - target_pos
        d_error = error - self.last_error
        
        pd_value = (error * cfg.INIT_Kp) + (d_error * cfg.INIT_Kd)
        self.last_error = error
        
        cmd = int(pd_value)
        
        # PID 모드일 때의 속도 제한
        if cmd > 0: cmd = min(cmd, cfg.MAX_PID_SPEED)
        else:       cmd = max(cmd, -cfg.MAX_PID_SPEED)
            
        # 최소 기동 전압 보정
        if 0 < abs(cmd) < 10:
            cmd = 10 * (1 if cmd > 0 else -1)
            
        return cmd, error

    def start_homing(self):
        print("[Motor] 호밍 명령(888) 전송")
        self.send_command(cfg.CMD_HOMING)
        self.last_error = 0

    def deploy_shield(self):
        print("[Motor] 디플로이(777) 전송")
        self.send_command(cfg.CMD_DEPLOY)

    def emergency_drop(self):
        self.send_command(cfg.CMD_FULL_DOWN) # -255

    def stop(self):
        self.send_command(cfg.CMD_STOP)

    def close(self):
        if self.ser:
            self.stop()
            self.ser.close()