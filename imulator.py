[1mdiff --git a/main.py b/main.py[m
[1mindex 635e0a7..6cc0cfe 100644[m
[1m--- a/main.py[m
[1m+++ b/main.py[m
[36m@@ -264,4 +264,6 @@[m [mdef get_incident([m
             detail="Incident not found"[m
         )[m
 [m
[31m-    return incident[m
\ No newline at end of file[m
[32m+[m[32m    return incident[m
[41m+[m
[41m+[m
[1mdiff --git a/simulator.py b/simulator.py[m
[1mindex 2ad4339..04057d7 100644[m
[1m--- a/simulator.py[m
[1m+++ b/simulator.py[m
[36m@@ -64,8 +64,8 @@[m [mdef send_error(error):[m
         else:[m
             print(f"[FAILED] Status {response.status_code}: {response.text}")[m
 [m
[31m-    except requests.exceptions.ConnectionError:[m
[31m-        print("[ERROR] FastAPI server se connect nahi ho paya.")[m
[32m+[m[32m    except requests.exceptions.RequestException as e:[m
[32m+[m[32m        print(f"[ERROR] Backend connection failed: {str(e)}")[m
 [m
 [m
 def run_simulator(num_errors=20, delay_seconds=1):[m
[36m@@ -80,14 +80,4 @@[m [mdef run_simulator(num_errors=20, delay_seconds=1):[m
 [m
 [m
 if __name__ == "__main__":[m
[31m-    run_simulator(num_errors=20, delay_seconds=1)[m
[31m-[m
[31m-def send_error(error):[m
[31m-    try:[m
[31m-        response = requests.post(API_URL, json=error, timeout=3)[m
[31m-        if response.status_code == 200:[m
[31m-            print("[SENT] Error queued successfully")[m
[31m-        else:[m
[31m-            print(f"[FAILED] Status {response.status_code}: {response.text}")[m
[31m-    except requests.exceptions.RequestException as e:[m
[31m-        print(f"[TIMEOUT] Backend took too long to respond")[m
\ No newline at end of file[m
[32m+[m[32m    run_simulator(num_errors=20, delay_seconds=1)[m
\ No newline at end of file[m
