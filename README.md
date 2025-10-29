
***⚡ NetPulse - Live Network Monitor***

NetPulse is a *lightweight*, *terminal-based* real-time network monitoring tool written in Python.  
It pings multiple endpoints and visualizes latency trends directly in your terminal — fast, minimal, and effective.

> Built for sysadmins, learners, bug bounty hunters & network nerds who love the terminal life.


***🔍 Features***

- Real-time ping stats with graphical trend
- Monitor multiple endpoints
- Supports DNS/HTTP/IP probes
- Fast & zero-bloat (no heavy libs)
- Works on Linux, WSL, and Termux


***📸 Preview***

```
Host:Port        Ping (ms)       Trend
8.8.8.8:53       64.5 ms         █▁█▃▂▃█▁▂█
1.1.1.1:53       72.2 ms         █▃█▂▁▂▅▃▁█
google.com:80    84.7 ms         ▂▁▃█▁▅▁▃█
```


***🚀 Getting Started***

```bash
git clone https://github.com/karndeepbaror/NetPulse
cd NetPulse
python netpulse.py
```

***🔧 Requirements***

```bash
pip install -r requirements.txt
```

***🛠 Customization***

- You can modify target hosts/ports directly inside the script.
- Tune `update_interval` or `probe_size` for faster/slower analysis.


***👤 Author***

*Karndeep Baror*
🔗 [LinkedIn Profile](https://www.linkedin.com/in/karndeepbaror)


***⚠️ Disclaimer***

This tool is for *educational and personal network diagnostic* use only.  
Using it against unauthorized servers may be illegal.


***_⭐ Star the repo if you like it!_***
