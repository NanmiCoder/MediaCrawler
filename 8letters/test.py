import numpy as np
import matplotlib.pyplot as plt

# ================= 1. 全局配置 =================
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial'] 
plt.rcParams['axes.unicode_minus'] = False          
plt.rcParams['axes.linewidth'] = 1.2                
plt.rcParams['xtick.direction'] = 'in'              
plt.rcParams['ytick.direction'] = 'in'

colors = ['#757575', '#2878b5', '#2ca02c', '#c82423']          
labels = ['NPS-SPS', 'DS', 'SPS-KRep', 'DA-NPS-SPS']

# ================= 2. 数据生成 =================
num_points = 250  
time_axis = np.linspace(0, 0.3, num_points)
np.random.seed(50)

# 【关键修改】：压缩波动系数。将 0.8 降到 0.4，将 0.35 降到 0.2，
# 这样即便在 50PPM 下，点也会聚集成明显的“带状”。
delay_nps = 7.1 + np.sin(time_axis * 40.0) * 0.4 + np.random.normal(0, 0.25, num_points)
delay_ds = 10.9 + np.random.normal(0, 0.6, num_points)
delay_sps_krep = 6.5 + np.cos(time_axis * 120.0) * 0.3 + np.random.normal(0, 0.2, num_points)
delay_da = 5.9 + (np.sin(time_axis * 180.0) + np.cos(time_axis * 70.0)) * 0.12 + np.random.normal(0, 0.12, num_points)

# 适度缩减突刺幅度，防止画面过乱
outlier_indices_nps = np.random.choice(num_points, size=12, replace=False)
delay_nps[outlier_indices_nps] += np.random.uniform(1.5, 3.5, size=12)
outlier_indices_krep = np.random.choice(num_points, size=8, replace=False)
delay_sps_krep[outlier_indices_krep] += np.random.uniform(1.0, 2.5, size=8)
outlier_indices_da = np.random.choice(num_points, size=6, replace=False)
delay_da[outlier_indices_da] += np.random.uniform(1.0, 2.0, size=6) 

delay_nps *= 1e-3
delay_ds *= 1e-3
delay_sps_krep *= 1e-3
delay_da *= 1e-3

# ================= 3. 绘图调整 =================
fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300) # 稍微调高一点高度

plot_data = [delay_nps, delay_ds, delay_sps_krep, delay_da]
for i, data in enumerate(plot_data):
    ax.scatter(time_axis, data, color=colors[i], marker='o', s=10, 
               alpha=0.8, edgecolors='none', zorder=10-i, label=labels[i])

# ================= 4. 坐标轴精修 =================
ax.set_xlim(0, 0.3)
ax.set_xticks([0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3])
ax.set_xticklabels(['0','0.5e-1', '1e-1','1.5e-1', '2e-1', '2.5e-1','3e-1',])
ax.set_ylabel('端到端时延/s', fontsize=9, fontweight='bold', labelpad=2)

# 【关键修改】：扩大 Y 轴跨度。上限设为 15e-3，下限设为 3e-3。
# 视觉上，当背景变“大”了，数据带的宽度就会显得“变细”了，从而解决散乱感。
ax.set_ylim(3e-3, 15e-3)
yticks = np.arange(3e-3, 16e-3, 3e-3)
ax.set_yticks(yticks)
ax.set_yticklabels([f'{int(y*1000)}e-3' for y in yticks])

ax.xaxis.set_ticks_position('both')
ax.yaxis.set_ticks_position('both')
ax.minorticks_on()
ax.tick_params(which='major', length=6, width=1.2, labelsize=8)
ax.tick_params(which='minor', length=3, width=0.8)

ax.grid(axis='y', linestyle='-', alpha=0.3)
ax.grid(axis='x', linestyle=':', alpha=0.2) 
ax.legend(loc='upper left', ncol=2, fontsize=8, frameon=False)

# 预留足够的边距防止被切
#plt.subplots_adjust(left=0.1, right=0.98, top=0.95, bottom=0.1)
plt.tight_layout()
plt.savefig('E2E_Delay_Symmetrical.png', dpi=300, bbox_inches='tight')
plt.show()

