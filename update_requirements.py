
import subprocess

def update_requirements():
    try:
        # 进入 mediacrawler 环境并运行命令 pip freeze，并将输出重定向到 requirements.txt 文件中
        subprocess.run(['conda', 'activate', 'mediacrawler', '&&', 'pip', 'list','--format=freeze'], check=True, capture_output=True, text=True, shell=True)
        output = subprocess.run(['conda', 'activate', 'mediacrawler', '&&', 'pip', 'list','--format=freeze'], check=True, capture_output=True, text=True, shell=True).stdout
        with open('requirements.txt', 'w') as f:
            f.write(output)
        print("requirements.txt 文件已更新")
    except subprocess.CalledProcessError as e:
        print("更新 requirements.txt 文件时出现错误:", e)

# 调用函数来更新 requirements.txt 文件
update_requirements()

