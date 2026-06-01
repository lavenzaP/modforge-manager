using Microsoft.UI.Xaml;

namespace ModForge.WinUI;

public partial class App : Application
{
    private Window? window;

    public App()
    {
        RequestedTheme = ApplicationTheme.Dark;
        InitializeComponent();
    }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        window = new MainWindow();
        window.Activate();
    }
}
