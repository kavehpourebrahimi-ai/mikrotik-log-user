Enterprise VMS - Windows Package

Contents:
- bin\vms_server.exe
- bin\vms_client.exe
- runtime DLL files
- config\vms-server.conf
- scripts\start-server.cmd
- scripts\start-client.cmd

Quick start:
1) Run scripts\start-server.cmd
2) Run scripts\start-client.cmd
3) Login with default credentials:
   username: admin
   password: admin

Industrial deployment notes:
- Change admin password immediately.
- Set Windows Firewall rules for API port 8080.
- Configure your production storage path in config\vms-server.conf.
- Run the server with a dedicated Windows service account.
