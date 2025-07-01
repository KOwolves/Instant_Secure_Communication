document.addEventListener('DOMContentLoaded', function() {
    const sign_in_btn = document.querySelector("#sign-in-btn");
    const sign_up_btn = document.querySelector("#sign-up-btn");
    const container = document.querySelector(".container");
    const signInForm = document.querySelector(".sign-in-form");
    const signUpForm = document.querySelector(".sign-up-form");

    // 切换到注册模式
    sign_up_btn.addEventListener("click", () => {
        container.classList.add("sign-up-mode");
    });

    // 切换到登录模式
    sign_in_btn.addEventListener("click", () => {
        container.classList.remove("sign-up-mode");
    });

    // 登录表单提交处理
    signInForm.addEventListener("submit", function(e) {
        e.preventDefault();
        const username = document.getElementById("login-username").value;
        const password = document.getElementById("login-password").value;

        if (!username || !password) {
            showAlert("请填写所有必填字段", "error");
            return;
        }

        // 使用表单方式提交
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        fetch('/api/login', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert("登录成功！正在跳转...", "success");
                setTimeout(() => {
                    window.location.href = "/dashboard";
                }, 1500);
            } else {
                showAlert(data.message || "登录失败，请检查用户名和密码", "error");
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert("发生错误，请稍后再试", "error");
        });
    });

    // 注册表单提交处理
    signUpForm.addEventListener("submit", function(e) {
        e.preventDefault();
        const username = document.getElementById("register-username").value;
        const password = document.getElementById("register-password").value;
        const confirmPassword = document.getElementById("register-confirm-password").value;

        if (!username || !password || !confirmPassword) {
            showAlert("请填写所有必填字段", "error");
            return;
        }

        if (password !== confirmPassword) {
            showAlert("两次输入的密码不一致", "error");
            return;
        }

        if (password.length < 6) {
            showAlert("密码长度至少为6位", "error");
            return;
        }

        // 使用表单方式提交
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        fetch('/api/register', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert("注册成功！请登录", "success");
                setTimeout(() => {
                    container.classList.remove("sign-up-mode");
                    document.getElementById("login-username").value = username;
                    window.location.href = "/dashboard";
                }, 1500);
            } else {
                showAlert(data.message || "注册失败，请稍后再试", "error");
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert("发生错误，请稍后再试", "error");
        });
    });

    // 显示提示框
    function showAlert(message, type) {
        const alertDiv = document.createElement("div");
        alertDiv.className = `alert ${type}`;
        alertDiv.textContent = message;
        document.body.appendChild(alertDiv);

        setTimeout(() => {
            alertDiv.style.opacity = "0";
            setTimeout(() => {
                document.body.removeChild(alertDiv);
            }, 500);
        }, 3000);
    }

    // 模拟登录响应（仅用于演示）
    function simulateLogin(username, password) {
        if (username && password) {
            showAlert("登录成功！正在跳转...", "success");
            // 跳转到主界面
            setTimeout(() => {
                window.location.href = "../template/main.html";
            }, 1500);
        } else {
            showAlert("登录失败，请检查用户名和密码", "error");
        }
    }

    // 模拟注册响应（仅用于演示）
    function simulateRegister(username, email, password) {
        if (username && email && password) {
            showAlert("注册成功！请登录", "success");
            setTimeout(() => {
                container.classList.remove("sign-up-mode");
                document.getElementById("login-username").value = username;
            }, 1500);
            // 实际项目中应删除此处，使用真实的后端响应
        } else {
            showAlert("注册失败，请稍后再试", "error");
        }
    }
}); 