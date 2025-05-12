#!/bin/bash

# 确保以root权限运行
if [ "$(id -u)" != "0" ]; then
   echo "此脚本需要以root权限运行，请使用 sudo" 1>&2
   exit 1
fi

# 配置参数
read -p "请输入本机名称（如 A/B/C）: " MACHINE_NAME
read -p "请输入服务端URL（如 http://server_ip:5000/update_status）: " SERVER_URL

# 安装依赖
apt-get update
apt-get install -y python3 python3-pip
pip3 install requests psutil nvidia-ml-py

# 创建安装目录
INSTALL_DIR="/opt/monitoring-agent/client"
mkdir -p $INSTALL_DIR

# 生成配置文件
cat > $INSTALL_DIR/client_config.py <<EOF
SERVER_URL = "$SERVER_URL"
MACHINE_NAME = "$MACHINE_NAME"
EOF

# 复制程序文件
cp client.py $INSTALL_DIR/
chmod +x $INSTALL_DIR/client.py

# 创建服务文件
cat > /etc/systemd/system/monitoring-client.service <<EOF
[Unit]
Description=Monitoring Client Service
After=network.target

[Service]
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/client.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动服务
systemctl daemon-reload
systemctl enable monitoring-client
systemctl start monitoring-client

echo "客户端安装完成！使用以下命令管理："
echo "systemctl status monitoring-client"