using System;
using System.Drawing;
using System.Windows.Forms;
using System.Diagnostics;
using System.IO;

namespace MNIMETray
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            
            // Check if we can find MNIME.exe or python + MNIME.py
            string basePath = AppDomain.CurrentDomain.BaseDirectory;
            string exePath = Path.Combine(basePath, "MNIME.exe");
            string pyPath = Path.Combine(basePath, ".venv", "Scripts", "pythonw.exe");
            string scriptPath = Path.Combine(basePath, "MNIME.py");
            
            NotifyIcon trayIcon = new NotifyIcon();
            trayIcon.Text = "MNIME";
            
            try {
                trayIcon.Icon = new Icon(Path.Combine(basePath, "MN.ico"));
            } catch {
                trayIcon.Icon = SystemIcons.Application;
            }
            
            ContextMenu trayMenu = new ContextMenu();
            trayMenu.MenuItems.Add("Show MNIME", (sender, e) => {
                LaunchMNIME(exePath, pyPath, scriptPath);
            });
            trayMenu.MenuItems.Add("-");
            trayMenu.MenuItems.Add("Quit", (sender, e) => {
                trayIcon.Visible = false;
                Application.Exit();
            });
            
            trayIcon.ContextMenu = trayMenu;
            trayIcon.Visible = true;
            
            trayIcon.DoubleClick += (sender, e) => {
                LaunchMNIME(exePath, pyPath, scriptPath);
            };
            
            Application.Run();
        }
        
        static void LaunchMNIME(string exePath, string pyPath, string scriptPath)
        {
            try
            {
                ProcessStartInfo startInfo = new ProcessStartInfo();
                startInfo.WindowStyle = ProcessWindowStyle.Hidden;
                startInfo.CreateNoWindow = true;
                
                if (File.Exists(exePath))
                {
                    startInfo.FileName = exePath;
                    startInfo.Arguments = "--managed";
                }
                else if (File.Exists(pyPath) && File.Exists(scriptPath))
                {
                    startInfo.FileName = pyPath;
                    startInfo.Arguments = string.Format("\"{0}\" --managed", scriptPath);
                }
                else
                {
                    MessageBox.Show("Could not find MNIME.exe or Python environment.", "MNIME Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }
                
                Process.Start(startInfo);
            }
            catch (Exception ex)
            {
                MessageBox.Show(string.Format("Failed to launch MNIME:\n{0}", ex.Message), "MNIME Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
