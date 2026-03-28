"""
启动本地HTTP服务器，用于访问数据看板
"""
import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """自定义HTTP请求处理器"""
    
    def end_headers(self):
        # 添加CORS头，允许跨域访问
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def log_message(self, format, *args):
        """自定义日志输出"""
        print(f"[{self.log_date_time_string()}] {format % args}")

def main():
    """启动HTTP服务器"""
    # 切换到项目根目录
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # 检查dashboard_data.json是否存在
    dashboard_data_path = project_root / 'dashboard' / 'dashboard_data.json'
    if not dashboard_data_path.exists():
        print("=" * 70)
        print("⚠️  警告: dashboard_data.json 文件不存在！")
        print("=" * 70)
        print("\n正在自动生成数据文件...")
        try:
            import export_dashboard_data
            exporter = export_dashboard_data.DashboardDataExporter()
            exporter.export_all()
            print("✅ 数据文件生成成功！\n")
        except Exception as e:
            print(f"❌ 生成数据文件失败: {e}")
            print("\n请手动运行: python export_dashboard_data.py")
            return
    
    # 启动服务器
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        dashboard_url = f"http://localhost:{PORT}/dashboard/index.html"
        
        print("=" * 70)
        print("🚀 数据看板服务器已启动")
        print("=" * 70)
        print(f"\n📍 访问地址: {dashboard_url}")
        print(f"📁 服务目录: {project_root}")
        print(f"\n💡 提示:")
        print(f"   - 按 Ctrl+C 停止服务器")
        print(f"   - 如果浏览器未自动打开，请手动访问上述地址")
        print("=" * 70)
        print()
        
        # 自动打开浏览器
        try:
            webbrowser.open(dashboard_url)
        except Exception as e:
            print(f"⚠️  无法自动打开浏览器: {e}")
            print(f"   请手动访问: {dashboard_url}\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 服务器已停止")

if __name__ == "__main__":
    main()
