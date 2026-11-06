// Autofarm.exe: opens the BTD6 Autofarm app (gui.py).
//   1. The app already open? Bring its window to the front instead of opening a second one.
//   2. Check for an update (updater.ps1 asks GitHub first, downloads only if there is one).
//      Skipped while the farm is running, so files don't change under a live game.
//   3. Start the app through uv, without a console window.
// Build: launcher\build.bat (uses the C# compiler that ships with Windows).
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
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
        string dir = AppDomain.CurrentDomain.BaseDirectory;
        IntPtr open = FindWindow(null, Title);
        if (open != IntPtr.Zero)
        {
            if (IsIconic(open)) ShowWindow(open, 9);    // SW_RESTORE
            SetForegroundWindow(open);
            return;
        }
        if (!File.Exists(Path.Combine(dir, "gui.py")))
        {
            MessageBox.Show("Unzip the folder first (right-click the zip, Extract All), then open Autofarm.exe from there.", Title);
            return;
        }
        string uv = FindUv();
        if (uv == null)
        {
            MessageBox.Show("uv isn't installed yet. Double-click Install.bat first.", Title);
            return;
        }

        bool updated = false;
        string updater = Path.Combine(dir, "updater.ps1");
        if (File.Exists(updater) && !FarmRunning(dir))
        {
            try
            {
                var psi = new ProcessStartInfo("powershell.exe",
                    "-NoProfile -ExecutionPolicy Bypass -File \"" + updater + "\"")
                {
                    WorkingDirectory = dir, UseShellExecute = false, CreateNoWindow = true,
                    RedirectStandardOutput = true, RedirectStandardError = true
                };
                using (var p = Process.Start(psi))
                {
                    p.StandardOutput.ReadToEnd();
                    p.StandardError.ReadToEnd();
                    if (p.WaitForExit(180000)) updated = p.ExitCode == 2;
                }
            }
            catch (Exception) { }       // no update today: open the app anyway
        }

        string uvw = Path.Combine(Path.GetDirectoryName(uv), "uvw.exe");
        string extra = updated ? " --updated" : "";
        var start = File.Exists(uvw)
            ? new ProcessStartInfo(uvw, "run gui.py" + extra)
            : new ProcessStartInfo(uv, "run --gui-script gui.py" + extra);
        start.WorkingDirectory = dir;
        start.UseShellExecute = false;
        start.CreateNoWindow = true;
        Process.Start(start);
    }

    // The farm writes a heartbeat to state.json every second while it runs.
    static bool FarmRunning(string dir)
    {
        try
        {
            string s = File.ReadAllText(Path.Combine(dir, "state.json"));
            var m = Regex.Match(s, "\"heartbeat\":\\s*([0-9.]+)");
            if (!m.Success) return false;
            double beat = double.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
            double now = (DateTime.UtcNow - new DateTime(1970, 1, 1)).TotalSeconds;
            return now - beat < 15 && !s.Contains("\"stopped\": true");
        }
        catch (Exception) { return false; }
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
