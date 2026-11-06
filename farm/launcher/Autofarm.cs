// Autofarm.exe: opens the BTD6 Autofarm app (farm\gui.py). It sits at the top of the download
// beside Install.bat; everything else lives in the farm folder.
//   1. The app already open? Bring its window to the front instead of opening a second one.
//   2. Start the app through uv, without a console window. The app checks for updates itself.
// Build: launcher\build.bat (uses the C# compiler that ships with Windows).
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;

static class Program
{
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern IntPtr FindWindow(string cls, string title);
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] static extern bool IsIconic(IntPtr h);

    const string Title = "BTD6 Autofarm";

    [STAThread]
    static void Main()
    {
        string dir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "farm");
        IntPtr open = FindWindow(null, Title);
        if (open != IntPtr.Zero)
        {
            if (IsIconic(open)) ShowWindow(open, 9);    // SW_RESTORE
            SetForegroundWindow(open);
            return;
        }
        if (!File.Exists(Path.Combine(dir, "gui.py")))
        {
            MessageBox.Show("Unzip the whole folder first (right-click the zip, Extract All), then open Autofarm.exe from there. It needs the farm folder next to it.", Title);
            return;
        }
        string uv = FindUv();
        if (uv == null)
        {
            MessageBox.Show("uv isn't installed yet. Double-click Install.bat first.", Title);
            return;
        }

        string uvw = Path.Combine(Path.GetDirectoryName(uv), "uvw.exe");
        var start = File.Exists(uvw)
            ? new ProcessStartInfo(uvw, "run gui.py")
            : new ProcessStartInfo(uv, "run --gui-script gui.py");
        start.WorkingDirectory = dir;
        start.UseShellExecute = false;
        start.CreateNoWindow = true;
        Process.Start(start);
    }

    // Where uv lands with each way Install.bat installs it.
    static string FindUv()
    {
        foreach (string d in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';'))
        {
            try
            {
                string p = Path.Combine(d.Trim(), "uv.exe");
                if (d.Trim().Length > 0 && File.Exists(p)) return p;
            }
            catch (Exception) { }
        }
        string home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string roaming = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        foreach (string p in new[] {
            Path.Combine(home, @".local\bin\uv.exe"), Path.Combine(home, @".cargo\bin\uv.exe"),
            Path.Combine(local, @"Microsoft\WinGet\Links\uv.exe") })
            if (File.Exists(p)) return p;
        try
        {
            string py = Path.Combine(roaming, "Python");
            if (Directory.Exists(py))
                foreach (string p in Directory.GetFiles(py, "uv.exe", SearchOption.AllDirectories)) return p;
        }
        catch (Exception) { }
        return null;
    }
}
