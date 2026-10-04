# Local JSON-line bridge. Never returns addresses, titles, or page contents.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes, WindowsBase
Add-Type -ReferencedAssemblies UIAutomationClient, UIAutomationTypes, WindowsBase -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Automation;
public static class PetFocus {
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
    [DllImport("user32.dll")] static extern IntPtr MonitorFromPoint(POINT p, uint flags);
    [DllImport("user32.dll", CharSet=CharSet.Auto)] static extern bool GetMonitorInfo(IntPtr h, ref MONITOR m);
    [DllImport("user32.dll")] static extern bool SetProcessDpiAwarenessContext(IntPtr v);
    [StructLayout(LayoutKind.Sequential)] struct POINT { public int x,y; }
    [StructLayout(LayoutKind.Sequential)] struct RECT { public int l,t,r,b; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Auto)] struct MONITOR {
        public int size; public RECT monitor, work; public uint flags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string device;
    }
    public sealed class Target {
        public string token, site, monitor;
        public double x,y; public int left,top;
        internal string identity; internal AutomationElement button;
    }
    static Target previous;
    public static string Reason = "starting";
    static Target Skip(string reason) { Reason=reason; previous=null; return null; }
    public static void Initialize() { try { SetProcessDpiAwarenessContext(new IntPtr(-4)); } catch {} }
    public static string Site(string value) {
        if (String.IsNullOrWhiteSpace(value) || value.IndexOfAny(new char[]{' ', '\t', '\r', '\n'}) >= 0) return null;
        if (!value.Contains("://")) value = "https://" + value;
        Uri u;
        if (!Uri.TryCreate(value, UriKind.Absolute, out u) ||
            (u.Scheme != "https" && u.Scheme != "http") || !String.IsNullOrEmpty(u.UserInfo)) return null;
        string host = u.DnsSafeHost.ToLowerInvariant();
        foreach (string site in new string[]{"instagram.com", "tiktok.com"})
            if (host == site || host.EndsWith("."+site, StringComparison.Ordinal)) return site;
        return null;
    }
    static List<AutomationElement> Chrome(AutomationElement root) {
        var result = new List<AutomationElement>();
        var queue = new Queue<Tuple<AutomationElement,int>>();
        queue.Enqueue(Tuple.Create(root,0));
        var walker = TreeWalker.ControlViewWalker;
        while (queue.Count > 0) {
            var entry = queue.Dequeue(); var e = entry.Item1;
            if (result.Count >= 512 || entry.Item2 > 18) throw new InvalidOperationException();
            // Never traverse a web document (including fake tab/close controls in a page).
            if (e.Current.ControlType == ControlType.Document) continue;
            result.Add(e);
            for (var c = walker.GetFirstChild(e); c != null; c = walker.GetNextSibling(c)) {
                if (queue.Count >= 512) throw new InvalidOperationException();
                queue.Enqueue(Tuple.Create(c,entry.Item2+1));
            }
        }
        return result;
    }
    static string Id(AutomationElement e) { return String.Join(",", e.GetRuntimeId()); }
    public static bool CloseName(string name) {
        string n=(name ?? "").Trim().ToLowerInvariant();
        int shortcut=n.IndexOf(" (");
        if (shortcut >= 0 && n.EndsWith(")")) n=n.Substring(0,shortcut);
        return n == "close" || n == "close tab" || n == "cerrar" || n == "cerrar pestaña";
    }
    static bool Address(AutomationElement e) {
        if (e.Current.ControlType != ControlType.Edit) return false;
        if (e.Current.AutomationId == "addressEditBox") return true;
        return AddressName(e.Current.Name);
    }
    public static bool AddressName(string name) {
        // Chrome on this Windows installation appends a space to its Spanish label.
        // Trim also accepts nonbreaking spaces without weakening the exact allowlist.
        string n = (name ?? "").Trim().ToLowerInvariant();
        return n == "address and search bar" || n == "search or enter web address" ||
            n == "address bar" || n == "barra de direcciones y de búsqueda" ||
            n == "barra de direcciones y búsqueda" || n == "barra de direcciones" ||
            n == "barra de búsqueda y direcciones";
    }
    public static Target Probe() { return ProbeWindow(GetForegroundWindow(), true); }
    static Target ProbeWindow(IntPtr hwnd, bool foregroundOnly) {
        try {
            Reason="reading_browser";
            uint pid;
            GetWindowThreadProcessId(hwnd, out pid);
            string process = Process.GetProcessById((int)pid).ProcessName.ToLowerInvariant();
            if (process != "chrome" && process != "msedge") return Skip("unsupported_window");
            var nodes = Chrome(AutomationElement.FromHandle(hwnd));
            AutomationElement address=null, tab=null;
            foreach (var e in nodes) {
                if (e.Current.IsOffscreen) continue;
                if (Address(e)) { if (address != null) throw new InvalidOperationException(); address=e; }
                if (e.Current.ControlType == ControlType.TabItem) {
                    object p;
                    if (e.TryGetCurrentPattern(SelectionItemPattern.Pattern, out p) && ((SelectionItemPattern)p).Current.IsSelected) {
                        if (tab != null) throw new InvalidOperationException(); tab=e;
                    }
                }
            }
            // The user explicitly permits closing the last tab (and its window).
            if (address == null) return Skip("address_unavailable");
            if (tab == null) return Skip("selected_tab_unavailable");
            if (address.Current.HasKeyboardFocus) return Skip("editing_address");
            object vp;
            if (!address.TryGetCurrentPattern(ValuePattern.Pattern, out vp)) return Skip("address_value_unavailable");
            string url = ((ValuePattern)vp).Current.Value;
            string site = Site(url);
            if (site == null) return Skip("allowed_site");
            AutomationElement button=null;
            foreach (var e in Chrome(tab)) {
                if (e.Current.ControlType != ControlType.Button || e.Current.IsOffscreen || !e.Current.IsEnabled) continue;
                string name=e.Current.Name.ToLowerInvariant(); object ip;
                if ((CloseName(name) ||
                     e.Current.AutomationId == "CloseTabButton") && e.TryGetCurrentPattern(InvokePattern.Pattern,out ip)) {
                    if (button != null) throw new InvalidOperationException(); button=e;
                }
            }
            if (button == null) return Skip("close_unavailable");
            if (foregroundOnly && GetForegroundWindow() != hwnd) return Skip("window_changed");
            var r=button.Current.BoundingRectangle;
            if (r.IsEmpty || r.Width < 2 || r.Height < 2 || r.Width > 100 || r.Height > 100) return Skip("close_geometry_unavailable");
            double x=r.X+r.Width/2, y=r.Y+r.Height/2;
            var m=new MONITOR(); m.size=Marshal.SizeOf(m);
            if (!GetMonitorInfo(MonitorFromPoint(new POINT{x=(int)x,y=(int)y},2),ref m)) return Skip("monitor_unavailable");
            string identity=pid.ToString()+"|"+hwnd.ToString()+"|"+url+"|"+Id(tab)+"|"+Id(button)+"|"+r.ToString();
            var target=new Target{identity=identity, site=site, button=button, x=x,y=y,
                monitor=m.device,left=m.monitor.l,top=m.monitor.t,
                token=previous != null && previous.identity == identity ? previous.token : Guid.NewGuid().ToString("N")};
            Reason="detected"; previous=target; return target;
        } catch { return Skip("accessibility_unavailable"); }
    }
    // Read-only developer diagnostic: never exposes page titles, URLs or close tokens.
    public static string[] Diagnose() {
        var results=new List<string>();
        foreach (string name in new string[]{"chrome","msedge"}) {
            foreach (var process in Process.GetProcessesByName(name)) {
                try {
                    if (process.MainWindowHandle == IntPtr.Zero) continue;
                    ProbeWindow(process.MainWindowHandle,false);
                    results.Add(name+":"+Reason);
                } catch { results.Add(name+":accessibility_unavailable"); }
            }
        }
        previous=null;
        return results.ToArray();
    }
    public static bool Close(string token) {
        if (previous == null || String.IsNullOrEmpty(token) || previous.token != token) return false;
        var fresh=Probe();
        if (fresh == null || fresh.token != token) return false;
        previous=null; // Single use, even if the browser presents an unsaved-draft dialog.
        try { ((InvokePattern)fresh.button.GetCurrentPattern(InvokePattern.Pattern)).Invoke(); return true; }
        catch { return false; }
    }
}
"@
[PetFocus]::Initialize()
Write-Output '{"ready":true}'
while ($null -ne ($line = [Console]::ReadLine())) {
    try {
        $request = $line | ConvertFrom-Json
        if ($request.command -eq 'probe') {
            $target = [PetFocus]::Probe()
            if ($null -eq $target) { @{target=$null;reason=[PetFocus]::Reason} | ConvertTo-Json -Compress }
            else {
                @{target=@{token=$target.token;site=$target.site;x=$target.x;y=$target.y;
                    monitor=$target.monitor;left=$target.left;top=$target.top}} | ConvertTo-Json -Compress
            }
        } elseif ($request.command -eq 'diagnose') {
            @{diagnostics=@([PetFocus]::Diagnose())} | ConvertTo-Json -Compress
        } elseif ($request.command -eq 'close') {
            @{closed=[PetFocus]::Close([string]$request.token)} | ConvertTo-Json -Compress
        } else { Write-Output '{"closed":false}' }
    } catch { Write-Output '{"target":null}' }
}
