import matplotlib.pyplot as plt

# 한글 폰트 설정 (환경에 맞춰 주석 해제/수정 필요)
# plt.rcParams['font.family'] = 'Malgun Gothic' 
plt.rcParams['axes.unicode_minus'] = False

# 데이터 정의 (수정된 값)
time = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
speed = [0, 2.0, 4.5, 7.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0]
target_pos = [0, 20, 45, 70, 90, 90, 90, 90, 90, 90, 90, 90]
actual_pos = [0, 10, 35, 65, 95, 98, 94, 88, 89, 90.5, 90, 90]

# 그래프 그리기
fig, ax1 = plt.subplots(figsize=(10, 6))

plt.title('캐리어 고속 이동(9m/s) 시 스토퍼 위치 제어응답 (오버슛 포함)', fontsize=14, pad=15)

# 왼쪽 Y축: 스토퍼 위치
ax1.set_xlabel('시간 (초)')
ax1.set_ylabel('스토퍼 위치 (cm)', color='black')
line1 = ax1.plot(time, target_pos, label='목표 위치 (Target)', color='blue', linestyle='--', linewidth=2)
line2 = ax1.plot(time, actual_pos, label='실제 위치 (Actual - Overshoot)', color='red', marker='o', linewidth=2)
ax1.tick_params(axis='y', labelcolor='black')
ax1.set_ylim(0, 120)

# 오른쪽 Y축: 캐리어 속도
ax2 = ax1.twinx()
ax2.set_ylabel('캐리어 속도 (m/s)', color='green')
line3 = ax2.plot(time, speed, label='캐리어 속도', color='green', alpha=0.3, linewidth=5)
ax2.tick_params(axis='y', labelcolor='green')
ax2.set_ylim(0, 12)

# 범례 및 그리드
lines = line1 + line2 + line3
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='lower right')
ax1.grid(True, linestyle=':', alpha=0.6)

# 오버슛 구간 강조 (화살표 및 텍스트)
ax1.annotate('오버슛 (Overshoot)', xy=(5, 98), xytext=(5, 110),
             arrowprops=dict(facecolor='black', shrink=0.05),
             ha='center', fontsize=10, color='red')

plt.tight_layout()
plt.show()