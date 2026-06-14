# 📦 ICE Private PyPI & Distribution Guide (v2.7.756)

This guide provides the DevOps standard for distributing the compiled ICE wheels (`.whl`) to your internal engineering teams, ensuring a seamless `pip install` developer experience.

## 1. The Problem: The "Wheel File" Dilemma
Simply emailing a `.whl` file to developers creates friction:
- Where do they store it?
- How is it version-controlled?
- How does it work in CI/CD and Docker builds?

The solution is to host it on a private repository that `pip` can natively connect to.

## 2. Solution: Private PyPI with `pypiserver`
A simple, secure way to host your packages is by using `pypiserver`.

### 📍 Server Setup (5 Minutes)
1.  **On a secure internal server, run:**
    ```bash
    pip install pypiserver
    mkdir -p ~/ice-packages
    ```
2.  **Copy your compiled wheels to the server:**
    ```bash
    scp dist/python/*.whl your-server:~/ice-packages/
    ```
3.  **Start the server:**
    ```bash
    pypiserver -p 8080 ~/ice-packages
    ```
    Your private repository is now live at `http://your-server-ip:8080`.

## 3. Developer Installation (The "Aha!" Moment)
Your developers no longer need to manage files. They use a standard `pip` command with the `--index-url` flag.

### `requirements.txt`
Update the project's `requirements.txt` to point to your new private index:
```
--index-url http://your-server-ip:8080
ice-engine==2.7.756
# or for internal use:
# ice-unlimited==2.7.756
```

Now, developers simply run:
```bash
pip install -r requirements.txt
```
It feels exactly like installing any other public package.

## 4. CI/CD & Docker Integration
Your Dockerfiles can now install ICE without needing to `COPY` the `.whl` file, keeping your image layers clean and your build process simple.

### `Dockerfile`
```dockerfile
# Add the --index-url to your pip install command
RUN pip install --no-cache-dir --index-url http://your-internal-repo:8080 -r requirements.txt
```

---
**DOPOVE PRIVATE LIMITED** (CIN: U62011TZ2026PTC037599) | [dopove.com](https://www.dopove.com/) | info@dopove.com  
**(c) 2026 DOPOVE PRIVATE LIMITED**
