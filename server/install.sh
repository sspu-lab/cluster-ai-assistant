#!/bin/bash

# 确保以root权限运行
if [ "$(id -u)" != "0" ]; then
   echo "此脚本需要以root权限运行，请使用 sudo" 1>&2
   exit 1
fi

# 安装依赖
apt-get update
apt-get install -y python3 python3-pip
pip3 install flask flask-cors requests psutil nvidia-ml-py

# 创建安装目录
INSTALL_DIR="/opt/monitoring-agent/server"
mkdir -p $INSTALL_DIR

# 配置内部机器
echo "配置内部机器（输入完成后按回车键继续）"
INTERNAL_MACHINES=""
while :
do
    read -p "请输入内部机器名称（留空结束）: " name
    if [ -z "$name" ]; then
        break
    fi
    read -p "请输入机器 $name 的IP地址: " ip
    INTERNAL_MACHINES+="\"$name\": \"http://$ip:5000\",\n"
done

# 生成配置文件
cat > $INSTALL_DIR/server_config.py <<EOF
INTERNAL_MACHINES = {
${INTERNAL_MACHINES::-2}
}
EOF

# 复制程序文件
cp server.py $INSTALL_DIR/
chmod +x $INSTALL_DIR/server.py

# 创建服务文件
cat > /etc/systemd/system/monitoring-server.service <<EOF
[Unit]
Description=Monitoring Server Service
After=network.target

[Service]
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/server.py
Restart=always
User=root
Environment=FLASK_ENV=production

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动服务
systemctl daemon-reload
systemctl enable monitoring-server
systemctl start monitoring-server

echo "服务端安装完成！使用以下命令管理："
echo "systemctl status monitoring-server"
echo "防火墙可能需要开放端口 5000"