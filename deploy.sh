#!/bin/bash
# NewAPI数据看板 - 一键部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -eq 0 ]; then
        print_info "检测到root用户"
    else
        print_info "当前用户: $(whoami)"
    fi
}

# 检查系统
check_system() {
    print_info "检查系统环境..."

    # 检查操作系统
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        print_info "操作系统: $NAME $VERSION"
    fi

    # 检查Docker
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        print_success "Docker已安装: $DOCKER_VERSION"
    else
        print_error "Docker未安装"
        read -p "是否安装Docker? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_docker
        else
            exit 1
        fi
    fi

    # 检查Docker Compose
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
        print_success "Docker Compose已安装: $COMPOSE_VERSION"
    else
        print_error "Docker Compose未安装"
        read -p "是否安装Docker Compose? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_docker_compose
        else
            exit 1
        fi
    fi
}

# 安装Docker
install_docker() {
    print_info "安装Docker..."

    # 更新包索引
    sudo apt-get update

    # 安装依赖
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # 添加Docker官方GPG密钥
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # 设置稳定版仓库
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # 安装Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io

    # 启动Docker
    sudo systemctl start docker
    sudo systemctl enable docker

    # 添加当前用户到docker组
    sudo usermod -aG docker $USER

    print_success "Docker安装完成"
}

# 安装Docker Compose
install_docker_compose() {
    print_info "安装Docker Compose..."

    sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose

    print_success "Docker Compose安装完成"
}

# 配置环境
setup_environment() {
    print_info "配置环境..."

    # 创建.env文件
    if [ ! -f .env ]; then
        cp .env.example .env
        print_success "创建.env配置文件"

        # 提示用户修改配置
        print_info "请编辑 .env 文件配置服务器参数"
        read -p "是否现在编辑? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-vi} .env
        fi
    else
        print_success ".env文件已存在"
    fi

    # 创建必要的目录
    mkdir -p logs backups
    print_success "创建必要目录"
}

# 构建和启动服务
deploy_services() {
    print_info "部署服务..."

    # 停止已有服务
    if docker-compose ps | grep -q "Up"; then
        print_info "停止现有服务..."
        docker-compose down
    fi

    # 构建镜像
    print_info "构建Docker镜像..."
    docker-compose build

    # 启动服务
    print_info "启动服务..."
    docker-compose up -d

    # 等待服务启动
    print_info "等待服务启动..."
    sleep 5

    # 检查服务状态
    docker-compose ps

    print_success "服务部署完成"
}

# 初始化数据
init_data() {
    print_info "初始化数据..."

    # 检查是否已有数据
    if [ ! -f newapi_warehouse.db ]; then
        print_info "数据库不存在，需要先同步数据"
        print_info "请参考文档手动执行数据同步"
        return
    fi

    # 执行一次完整的ETL和导出
    print_info "执行数据更新..."
    docker-compose exec app python3 daily_update.py

    print_success "数据初始化完成"
}

# 显示访问信息
show_info() {
    echo ""
    print_success "="*70
    print_success "部署完成！"
    print_success "="*70
    echo ""

    # 获取服务器IP
    SERVER_IP=$(hostname -I | awk '{print $1}')

    echo "访问地址:"
    echo "  - http://${SERVER_IP}"
    echo "  - http://localhost (本地)"
    echo ""

    echo "查看日志:"
    echo "  docker-compose logs -f"
    echo ""

    echo "查看服务状态:"
    echo "  docker-compose ps"
    echo ""

    echo "停止服务:"
    echo "  docker-compose down"
    echo ""

    echo "重启服务:"
    echo "  docker-compose restart"
    echo ""

    echo "更新数据:"
    echo "  docker-compose exec app python3 daily_update.py"
    echo ""

    echo "备份数据库:"
    echo "  ./deploy/backup.sh"
    echo ""

    print_success "详细文档请查看: DEPLOYMENT.md"
}

# 主函数
main() {
    clear
    echo ""
    echo "========================================="
    echo "   NewAPI 数据看板 - 一键部署脚本"
    echo "========================================="
    echo ""

    # 检查root
    check_root

    # 检查系统
    check_system

    # 配置环境
    setup_environment

    # 部署服务
    deploy_services

    # 初始化数据（可选）
    read -p "是否执行数据初始化? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        init_data
    fi

    # 显示信息
    show_info
}

# 运行主函数
main
