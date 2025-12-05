# =========================================
SYSTEM_MODE = 'CATCHING' 
# =========================================

# 통신 및 하드웨어
SERIAL_PORT = "COM5"
BAUD_RATE = 9600
CAM_INDEX = 0 
MODEL_PATH = 'yolo11m_1129.pt'
CONFIG_FILE = "ocam_control_config.json"
CALIB_FILE = "camera_calib_result.json"

# 공통 감지 파라미터
INIT_VEL_THRESH = 200.0   # 낙하 판단 속도
INIT_TRIG_FRAMES = 1      # 발동 민감도
SMOOTHING_FACTOR = 0.4    # 좌표 노이즈 필터
INIT_COOLDOWN = 2.0       # PID 모드용 쿨다운

# -----------------------------------------
# [PID 제어 파라미터] (Tracking 모드용)
# -----------------------------------------
INIT_Kp = 2.0
INIT_Kd = 1.0
BLOCKING_OFFSET = 0.0     # 캐리어와 동일 위치 유지
MAX_PID_SPEED = 200       # PID 모드에서의 최대 속도

# -----------------------------------------
# [Catching 모드 파라미터] (급강하용)
# -----------------------------------------
MAX_DROP_SPEED = 255      # 급강하 시 PWM (최대)
HOMING_TIMEOUT = 10.0     # 호밍 대기 시간

# -----------------------------------------
# [아두이노 명령 프로토콜]
# -----------------------------------------
CMD_STOP = 0
CMD_HOMING = 888          # 호밍 (센서 원점 탐색)
CMD_DEPLOY = 777          # 디플로이 (서보 동작)
CMD_FULL_DOWN = -255      # 수동 급강하 명령