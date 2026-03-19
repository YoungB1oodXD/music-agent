Changed transcript log path in tests/simulate_session.py from docs/ to data/logs/ to avoid modifying tracked files.  
The script uses a TeeOutput class to handle UnicodeEncodeError when printing to console, which was preserved. 
