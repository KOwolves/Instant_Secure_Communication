document.addEventListener('DOMContentLoaded', function() {
    const sign_in_btn = document.querySelector("#sign-in-btn");
    const sign_up_btn = document.querySelector("#sign-up-btn");
    const container = document.querySelector(".container");
    const signInForm = document.querySelector(".sign-in-form");
    const signUpForm = document.querySelector(".sign-up-form");
    const inputFields = document.querySelectorAll(".input-field");

    // 为所有输入框添加焦点效果
    inputFields.forEach(inputField => {
        const input = inputField.querySelector('input');
        const icon = inputField.querySelector('i');
        
        input.addEventListener('focus', () => {
            inputField.classList.add('active');
            icon.style.color = '#3498db';
        });
        
        input.addEventListener('blur', () => {
            if (input.value === '') {
                inputField.classList.remove('active');
                icon.style.color = '#999';
            }
        });
        
        // 如果输入框已经有值，添加active类
        if(input.value !== '') {
            inputField.classList.add('active');
        }
    });

    // 添加按钮波纹效果
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('mousedown', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const ripple = document.createElement('span');
            ripple.classList.add('ripple');
            ripple.style.left = `${x}px`;
            ripple.style.top = `${y}px`;
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });

    // 切换到注册模式
    sign_up_btn.addEventListener("click", () => {
        container.classList.add("sign-up-mode");
        animateFields(signUpForm.querySelectorAll('.input-field'));
    });

    // 切换到登录模式
    sign_in_btn.addEventListener("click", () => {
        // 添加过渡类，以便在适当时机显示聊天气泡
        container.classList.add("sign-up-mode-exit");
        container.classList.remove("sign-up-mode");
        animateFields(signInForm.querySelectorAll('.input-field'));
        
        // 过渡完成后移除过渡类
        setTimeout(() => {
            container.classList.remove("sign-up-mode-exit");
        }, 3000);
    });

    // 动画输入框显示效果
    function animateFields(fields) {
        fields.forEach((field, index) => {
            field.style.animation = `fadeInSlide 0.5s ease forwards ${index * 0.1 + 0.2}s`;
            field.style.opacity = '0';
        });
    }

    // 初始化时为登录表单添加动画
    setTimeout(() => {
        animateFields(signInForm.querySelectorAll('.input-field'));
    }, 200);

    // 登录表单提交处理
    signInForm.addEventListener("submit", function(e) {
        e.preventDefault();
        const username = document.getElementById("login-username").value;
        const password = document.getElementById("login-password").value;

        if (!username || !password) {
            showAlert("请填写所有必填字段", "error");
            shake(e.target);
            return;
        }

        // 显示登录按钮加载状态
        const submitBtn = this.querySelector('.btn');
        submitBtn.innerHTML = '<span class="btn-loading"></span>登录中...';
        submitBtn.disabled = true;

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
                shake(e.target);
                submitBtn.innerHTML = '登录';
                submitBtn.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert("发生错误，请稍后再试", "error");
            shake(e.target);
            submitBtn.innerHTML = '登录';
            submitBtn.disabled = false;
        });
    });

    // 注册表单提交处理
    signUpForm.addEventListener("submit", function(e) {
        e.preventDefault();
        const username = document.getElementById("register-username").value;
        const email = document.getElementById("register-email").value;
        const password = document.getElementById("register-password").value;
        const confirmPassword = document.getElementById("register-confirm-password").value;

        if (!username || !email || !password || !confirmPassword) {
            showAlert("请填写所有必填字段", "error");
            shake(e.target);
            return;
        }

        if (password !== confirmPassword) {
            showAlert("两次输入的密码不一致", "error");
            shake(document.getElementById("register-confirm-password").parentElement);
            return;
        }

        if (password.length < 6) {
            showAlert("密码长度至少为6位", "error");
            shake(document.getElementById("register-password").parentElement);
            return;
        }

        // 显示注册按钮加载状态
        const submitBtn = this.querySelector('.btn');
        submitBtn.innerHTML = '<span class="btn-loading"></span>注册中...';
        submitBtn.disabled = true;

        // 使用表单方式提交
        const formData = new FormData();
        formData.append('username', username);
        formData.append('email', email);
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
                    setTimeout(() => {
                        animateFields(signInForm.querySelectorAll('.input-field'));
                    }, 500);
                }, 1500);
            } else {
                showAlert(data.message || "注册失败，请稍后再试", "error");
                shake(e.target);
                submitBtn.innerHTML = '注册';
                submitBtn.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert("发生错误，请稍后再试", "error");
            shake(e.target);
            submitBtn.innerHTML = '注册';
            submitBtn.disabled = false;
        });
    });

    // 抖动效果
    function shake(element) {
        element.classList.add('shake');
        setTimeout(() => {
            element.classList.remove('shake');
        }, 500);
    }

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