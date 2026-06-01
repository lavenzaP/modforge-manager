using System;
using System.Windows;

namespace ModForge.App
{
    public static class Program
    {
        [STAThread]
        public static void Main()
        {
            var telemetry = new StartupTelemetry();
            telemetry.Mark("process-start");

            var application = new Application();
            application.ShutdownMode = ShutdownMode.OnMainWindowClose;

            var sidecar = new ShellPythonSidecarService();
            var window = new MainWindow(sidecar, telemetry);
            application.MainWindow = window;

            telemetry.Mark("main-window-created");
            window.Show();
            telemetry.Mark("main-window-shown");
            window.RefreshTelemetry();

            application.Run(window);
        }
    }
}
