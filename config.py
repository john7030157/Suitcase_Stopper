# =========================================
SYSTEM_MODE = 'CATCHING' 
# =========================================

# 공통 하드웨어 설정
SERIAL_PORT = "COM5"
BAUD_RATE = 9600
CAM_INDEX = 0           # 0: 노트북, 1: oCam
MODEL_PATH = 'yolo11m_1129.pt'
CONFIG_FILE = "ocam_control_config.json"
CALIB_FILE = "camera_calib_result.json"

# 제어 상수 (공통)
CONTROL_FPS = 30.0
INIT_VEL_THRESH = 200.0   # 낙상 판단 속도
INIT_TRIG_FRAMES = 1
INIT_COOLDOWN = 2.0
SMOOTHING_FACTOR = 0.4
VELOCITY_DEADZONE = 10.0
MAX_SPEED_UP = 255

# 모드별 특화 설정 (PID 및 오프셋)
if SYSTEM_MODE == 'TRACKING':
    # Tracking 모드 설정
    INIT_Kp = 2.0
    INIT_Kd = 1.0
    BLOCKING_OFFSET = 0.0     # 딱 맞춰서 막음
    MAX_SPEED_DOWN = 40       # 천천히 내려옴
    ENABLE_EMERGENCY_DROP = False

else: # 'CATCHING'
    # Catching 모드 설정 (더 빠르고 공격적)
    INIT_Kp = 5.0
    INIT_Kd = 1.0
    BLOCKING_OFFSET = 40.0    # 40% 앞서 가서 대기
    MAX_SPEED_DOWN = 30
    ENABLE_EMERGENCY_DROP = True
    EMERGENCY_DROP_SPEED = 150 # 이 속도 미만일 때 777 발동