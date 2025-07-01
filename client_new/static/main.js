document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const menuItems = document.querySelectorAll('.menu-item');
    const panels = document.querySelectorAll('.panel');
    const chatItems = document.querySelectorAll('.chat-item');
    const chatWindow = document.querySelector('.chat-window');
    const backBtn = document.querySelector('.chat-window .back-btn');
    const addFriendBtn = document.getElementById('add-friend-btn');
    const manageFriendsBtn = document.getElementById('manage-friends-btn');
    const addFriendModal = document.getElementById('add-friend-modal');
    const manageFriendsModal = document.getElementById('manage-friends-modal');
    const closeButtons = document.querySelectorAll('.modal .close');
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    const settingsBtn = document.getElementById('settings-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const sendBtn = document.querySelector('.send-btn');
    const messageInput = document.querySelector('.input-box input');
    const contactItems = document.querySelectorAll('.contact-item');
    const createGroupBtn = document.getElementById('create-group-btn');
    const createGroupModal = document.getElementById('create-group-modal');
    const groupNameInput = document.getElementById('group-name-input');
    const selectedMembersCount = document.getElementById('selected-members-count');
    const selectedMembersList = document.getElementById('selected-members-list');
    const confirmCreateGroupBtn = document.getElementById('confirm-create-group');
    const groupMembersBtn = document.getElementById('group-members-btn');
    const dissolveGroupBtn = document.getElementById('dissolve-group-btn');
    const groupMembersModal = document.getElementById('group-members-modal');
    const dissolveGroupBtnModal = document.getElementById('dissolve-group-btn-modal');
    const emojiPickerBtn = document.getElementById('emoji-picker-btn');
    const emojiPickerModal = document.getElementById('emoji-picker-modal');
    const emojis = document.querySelectorAll('.emoji');
    const imageUploadBtn = document.getElementById('image-upload-btn');
    const imageUploadInput = document.getElementById('image-upload-input');
    
    // 存储群组信息
    const groupChats = [];

    // 聊天记录存储（用于切换聊天对象时保持聊天记录）
    const chatHistory = {};
    
    // 当前聊天对象
    let currentChat = null;
    let isCurrentChatGroup = false;
    
    // 全局存储所有好友和在线好友
    window.allFriendsList = [];
    window.onlineFriendsList = [];
    window.currentUserId = ''; // 存储当前用户ID
    
    // 初始化获取当前用户ID
    fetch('/api/get_current_user', {
        method: 'GET',
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.user_id) {
            window.currentUserId = data.user_id.toString(); // 确保ID为字符串
            console.log('已获取当前用户ID:', window.currentUserId);
            
            // 初始化好友列表（确保用户ID获取后再加载好友列表）
            fetchFriendsList();
        } else {
            console.error('获取当前用户ID失败:', data.message || '未知错误');
        }
    })
    .catch(error => {
        console.error('获取当前用户ID失败:', error);
    });
    
    // 获取好友列表函数
    function fetchFriendsList() {
        if (!window.currentUserId) {
            console.error('无法获取好友列表：用户ID未设置');
            return;
        }
        
        fetch('/api/refresh_friends', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_id: window.currentUserId }),
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.onlineFriendsList = Array.isArray(data.online_friends) ? data.online_friends : [];
                window.allFriendsList = Array.isArray(data.all_friends) ? data.all_friends : [];
                console.log('初始化好友列表成功，在线好友:', window.onlineFriendsList.length, '所有好友:', window.allFriendsList.length);
            } else {
                console.error('初始化好友列表失败:', data.message);
            }
        })
        .catch(error => {
            console.error('获取初始好友列表出错:', error);
        });
    }
    
    // 生成随机颜色头像
    function generateAvatarColor(name) {
        // 根据名称生成确定的颜色（相同名称总是生成相同颜色）
        let hash = 0;
        for (let i = 0; i < name.length; i++) {
            hash = name.charCodeAt(i) + ((hash << 5) - hash);
        }
        
        // 生成HSL颜色，保持饱和度和亮度固定，只变化色相
        const hue = Math.abs(hash % 360);
        const saturation = 70; // 70%饱和度
        const lightness = 60;  // 60%亮度
        
        return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
    }
    
    // 生成头像HTML（显示名称首字母）
    function generateAvatar(name) {
        const bgColor = generateAvatarColor(name);
        const initial = name.charAt(0).toUpperCase();
        
        return `
            <div class="avatar-circle" style="background-color: ${bgColor};">
                <span class="avatar-initial">${initial}</span>
            </div>
        `;
    }

    // 替换现有头像为彩色头像
    function replaceAvatars() {
        // 替换聊天列表中的头像
        document.querySelectorAll('.chat-item .avatar').forEach(avatar => {
            const nameElement = avatar.closest('.chat-item').querySelector('.name');
            if (nameElement) {
                const name = nameElement.textContent;
                avatar.innerHTML = generateAvatar(name);
            }
        });
        
        // 替换联系人列表中的头像
        document.querySelectorAll('.contact-item .avatar').forEach(avatar => {
            const nameElement = avatar.closest('.contact-item').querySelector('.name');
            if (nameElement) {
                const name = nameElement.textContent;
                avatar.innerHTML = generateAvatar(name);
            }
        });
        
        // 替换消息中的头像
        document.querySelectorAll('.message.received .avatar').forEach(avatar => {
            const nameElement = document.querySelector('.chat-window .title');
            if (nameElement) {
                const name = nameElement.textContent;
                avatar.innerHTML = generateAvatar(name);
            }
        });
        
        // 替换个人资料卡片中的头像
        const profileAvatar = document.querySelector('.profile-card .avatar');
        if (profileAvatar) {
            profileAvatar.innerHTML = generateAvatar('当前用户');
        }
        
        // 替换侧边栏头像
        const sidebarAvatar = document.querySelector('.sidebar .avatar');
        if (sidebarAvatar) {
            sidebarAvatar.innerHTML = generateAvatar('当前用户');
        }
        
        // 替换好友管理界面中的头像
        document.querySelectorAll('.friend-item .avatar').forEach(avatar => {
            const nameElement = avatar.closest('.friend-item').querySelector('.name');
            if (nameElement) {
                const name = nameElement.textContent;
                avatar.innerHTML = generateAvatar(name);
            }
        });
        
        // 替换好友请求中的头像
        document.querySelectorAll('.request-item .avatar').forEach(avatar => {
            const nameElement = avatar.closest('.request-item').querySelector('.name');
            if (nameElement) {
                const name = nameElement.textContent;
                avatar.innerHTML = generateAvatar(name);
            }
        });
    }

    // 初始化界面
    updateMobileView();
    // 初始化好友管理界面
    updateFriendManagementUI();
    // 替换头像
    replaceAvatars();
    
    // 群成员查看按钮
    if (groupMembersBtn) {
        groupMembersBtn.addEventListener('click', function() {
            if (isCurrentChatGroup && currentChat) {
                // 查找当前群组
                const group = groupChats.find(g => g.name === currentChat);
                if (group) {
                    showGroupMembersModal(group);
                }
            }
        });
    }

    // 显示群成员模态框
    function showGroupMembersModal(group) {
        // 填充群组信息
        const groupNameElement = groupMembersModal.querySelector('.group-name-display');
        const memberCountElement = document.getElementById('member-count');
        const membersListElement = groupMembersModal.querySelector('.members-list');
        const groupAvatarElement = groupMembersModal.querySelector('.avatar');

        // 设置群组名称和头像
        groupNameElement.textContent = group.name;
        groupAvatarElement.innerHTML = generateAvatar(group.name);
        
        // 设置成员数量
        memberCountElement.textContent = group.members.length;
        
        // 填充成员列表
        membersListElement.innerHTML = '';
        group.members.forEach(member => {
            const memberElement = document.createElement('div');
            memberElement.className = 'member-item';
            memberElement.innerHTML = `
                <div class="avatar">${generateAvatar(member)}</div>
                <div class="name">${member}</div>
            `;
            membersListElement.appendChild(memberElement);
        });
        
        // 显示模态框
        groupMembersModal.style.display = 'flex';
    }

    // 解散群聊按钮（聊天窗口）
    if (dissolveGroupBtn) {
        dissolveGroupBtn.addEventListener('click', function() {
            if (isCurrentChatGroup && currentChat) {
                if (confirm(`确定要解散群聊"${currentChat}"吗？`)) {
                    dissolveGroup(currentChat);
                }
            }
        });
    }

    // 解散群聊按钮（模态框内）
    if (dissolveGroupBtnModal) {
        dissolveGroupBtnModal.addEventListener('click', function() {
            const groupName = groupMembersModal.querySelector('.group-name-display').textContent;
            if (confirm(`确定要解散群聊"${groupName}"吗？`)) {
                dissolveGroup(groupName);
                groupMembersModal.style.display = 'none';
            }
        });
    }

    // 解散群聊
    function dissolveGroup(groupName) {
        // 从群组列表中移除
        const groupIndex = groupChats.findIndex(g => g.name === groupName);
        if (groupIndex > -1) {
            groupChats.splice(groupIndex, 1);
        }
        
        // 从聊天列表中移除
        const chatListItem = document.querySelector(`.chat-item[data-name="${groupName}"]`);
        if (chatListItem) {
            chatListItem.remove();
        }
        
        // 从通讯录中移除
        const contactListItem = document.querySelector(`.contact-item[data-name="${groupName}"]`);
        if (contactListItem) {
            contactListItem.remove();
        }
        
        // 如果当前正在查看该群聊，返回到消息列表
        if (currentChat === groupName) {
            // 切换到消息面板
            menuItems.forEach(menuItem => {
                if (menuItem.getAttribute('data-panel') === 'chats') {
                    menuItem.click();
                }
            });
            
            // 隐藏聊天窗口（移动端）
            chatWindow.classList.remove('active');
            
            // 清空当前聊天
            currentChat = null;
            isCurrentChatGroup = false;
        }
        
        // 显示提示消息
        alert(`群聊"${groupName}"已解散`);
    }
    
    // 关闭群成员模态框
    if (groupMembersModal) {
        const closeBtn = groupMembersModal.querySelector('.close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                groupMembersModal.style.display = 'none';
            });
        }
    }
    
    // 存储已选择的群组成员
    let selectedMembers = [];
    
    // 创建群组按钮
    if (createGroupBtn) {
        createGroupBtn.addEventListener('click', function() {
            // 清空之前的选择
            selectedMembers = [];
            selectedMembersCount.textContent = '0';
            selectedMembersList.innerHTML = '';
            groupNameInput.value = '';
            
            // 填充联系人选择列表
            populateContactSelection();
            
            // 显示创建群组模态框
            createGroupModal.style.display = 'flex';
            
            // 禁用创建按钮，直到选择了成员并输入了名称
            updateCreateButtonState();
        });
    }
    
    // 监听群组名称输入变化
    if (groupNameInput) {
        groupNameInput.addEventListener('input', updateCreateButtonState);
    }
    
    // 确认创建群组按钮
    if (confirmCreateGroupBtn) {
        confirmCreateGroupBtn.addEventListener('click', function() {
            const groupName = groupNameInput.value.trim();
            
            if (groupName && selectedMembers.length > 0) {
                // 创建群组
                createGroup(groupName, selectedMembers);
                
                // 关闭模态框
                createGroupModal.style.display = 'none';
            }
        });
    }

    // 切换菜单项
    menuItems.forEach(item => {
        item.addEventListener('click', function() {
            const panelId = this.getAttribute('data-panel');
            
            // 更新菜单项状态
            menuItems.forEach(menuItem => {
                menuItem.classList.remove('active');
            });
            this.classList.add('active');
            
            // 更新面板显示
            panels.forEach(panel => {
                panel.classList.remove('active');
                if (panel.id === panelId + '-panel') {
                    panel.classList.add('active');
                }
            });
            // 如果切换到通讯录，刷新好友列表
            if (panelId === 'contacts') {
                console.log("切换到通讯录页面，正在获取最新好友列表...");
                // 显示加载状态
                const contactList = document.querySelector('.contacts .list');
                if (contactList) {
                    contactList.innerHTML = '<div class="loading-indicator">正在加载好友列表...</div>';
                }
                
                // 获取当前用户ID
                const userId = window.currentUserId || '';
                
                if (!userId) {
                    console.error('无法获取当前用户ID，无法刷新好友列表');
                    if (contactList) {
                        contactList.innerHTML = '<div class="error-message">无法获取用户ID，请重新登录</div>';
                    }
                    return;
                }
                
                console.log('使用用户ID刷新好友列表:', userId, '类型:', typeof userId);
                
                fetch('/api/refresh_friends', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ user_id: userId }),
                    credentials: 'same-origin' // 确保发送cookie以维持会话
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`服务器响应错误: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('收到服务器响应:', data);
                    if (data.success) {
                        // 确保即使返回null或undefined也始终有数组
                        window.onlineFriendsList = Array.isArray(data.online_friends) ? data.online_friends : [];
                        window.allFriendsList = Array.isArray(data.all_friends) ? data.all_friends : [];
                        console.log("成功获取好友列表，在线好友:", window.onlineFriendsList.length, "所有好友:", window.allFriendsList.length);
                        renderContacts();
                    } else {
                        console.error("获取好友列表失败:", data.message);
                        const contactList = document.querySelector('.contacts .list');
                        if (contactList) {
                            contactList.innerHTML = '<div class="error-message">获取好友列表失败: ' + (data.message || '未知错误') + '</div>';
                            // 添加重试按钮
                            const retryButton = document.createElement('button');
                            retryButton.className = 'retry-btn';
                            retryButton.textContent = '重试';
                            retryButton.addEventListener('click', function() {
                                // 模拟点击"通讯录"菜单项以刷新
                                const contactsMenuItem = document.querySelector('[data-panel="contacts"]');
                                if (contactsMenuItem) {
                                    contactsMenuItem.click();
                                }
                            });
                            contactList.appendChild(retryButton);
                        }
                    }
                })
                .catch(error => {
                    console.error("获取好友列表出错:", error);
                    const contactList = document.querySelector('.contacts .list');
                    if (contactList) {
                        contactList.innerHTML = '<div class="error-message">网络错误: ' + error.message + '</div>';
                        // 添加重试按钮
                        const retryButton = document.createElement('button');
                        retryButton.className = 'retry-btn';
                        retryButton.textContent = '重试';
                        retryButton.addEventListener('click', function() {
                            // 模拟点击"通讯录"菜单项以刷新
                            const contactsMenuItem = document.querySelector('[data-panel="contacts"]');
                            if (contactsMenuItem) {
                                contactsMenuItem.click();
                            }
                        });
                        contactList.appendChild(retryButton);
                    }
                });
            }
        });
    });

    // 点击聊天项打开聊天窗口 - 修复聊天切换问题
    function setupChatItemClickHandlers() {
        const chatItems = document.querySelectorAll('.chat-item');
        
        chatItems.forEach(item => {
            // 移除之前的事件监听器（如果有）
            const clone = item.cloneNode(true);
            item.parentNode.replaceChild(clone, item);
            
            // 添加新的事件监听器
            clone.addEventListener('click', function() {
                // 更新所有聊天项的选中状态
                document.querySelectorAll('.chat-item').forEach(chat => chat.classList.remove('selected'));
                this.classList.add('selected');
                
                const name = this.querySelector('.name').textContent;
                const latestMsg = this.querySelector('.message').textContent;
                
                console.log("点击聊天项：", name); // 调试信息
                
                // 更新聊天窗口标题
                document.querySelector('.chat-window .title').textContent = name;
                
                // 获取或创建此联系人的聊天记录
                if (!chatHistory[name]) {
                    // 为新聊天创建初始消息
                    chatHistory[name] = [
                        {
                            type: 'received',
                            content: latestMsg,
                            time: getCurrentTime()
                        }
                    ];
                }
                
                // 更新聊天窗口内容
                updateChatWindowContent(name);
                
                // 显示聊天窗口（特别是在移动设备上）
                if (window.innerWidth <= 768) {
                    chatWindow.classList.add('active');
                }
            });
        });
    }
    
    // 初始设置聊天项点击处理程序
    setupChatItemClickHandlers();
    
    // 点击联系人项打开聊天窗口 - 修复聊天框切换问题
    function setupContactItemClickHandlers() {
        // 获取所有联系人项
        const contactItems = document.querySelectorAll('.contact-item');
        
        contactItems.forEach(item => {
            // 移除之前的事件监听器（如果有）
            const clone = item.cloneNode(true);
            item.parentNode.replaceChild(clone, item);
            
            // 添加新的事件监听器
            clone.addEventListener('click', function() {
                const name = this.querySelector('.name').textContent;
                console.log("点击联系人：", name); // 调试信息
                
                // 切换到消息面板
                menuItems.forEach(menuItem => {
                    menuItem.classList.remove('active');
                    if (menuItem.getAttribute('data-panel') === 'chats') {
                        menuItem.classList.add('active');
                    }
                });
                
                panels.forEach(panel => {
                    panel.classList.remove('active');
                    if (panel.id === 'chats-panel') {
                        panel.classList.add('active');
                    }
                });
                
                // 查找或创建与该联系人的聊天项
                let chatItem = null;
                const existingChatItems = document.querySelectorAll('.chat-item');
                
                for (let i = 0; i < existingChatItems.length; i++) {
                    if (existingChatItems[i].querySelector('.name').textContent === name) {
                        chatItem = existingChatItems[i];
                        break;
                    }
                }
                
                if (!chatItem) {
                    // 如果不存在，创建新的聊天项
                    const chatList = document.querySelector('.chat-list .list');
                    const newChatItem = document.createElement('div');
                    newChatItem.className = 'chat-item';
                    newChatItem.innerHTML = `
                        <div class="avatar">
                            ${generateAvatar(name)}
                        </div>
                        <div class="content">
                            <div class="name">${name}</div>
                            <div class="message">点击开始聊天</div>
                        </div>
                        <div class="time">${getCurrentTime()}</div>
                    `;
                    
                    chatList.prepend(newChatItem);
                    
                    // 添加新的聊天历史
                    if (!chatHistory[name]) {
                        chatHistory[name] = [];
                    }
                    
                    // 为新创建的聊天项添加点击事件
                    newChatItem.addEventListener('click', function() {
                        const allChatItems = document.querySelectorAll('.chat-item');
                        allChatItems.forEach(chat => chat.classList.remove('selected'));
                        this.classList.add('selected');
                        
                        const itemName = this.querySelector('.name').textContent;
                        
                        document.querySelector('.chat-window .title').textContent = itemName;
                        updateChatWindowContent(itemName);
                        
                        if (window.innerWidth <= 768) {
                            chatWindow.classList.add('active');
                        }
                    });
                    
                    chatItem = newChatItem;
                } else {
                    // 更新现有聊天项的选中状态
                    existingChatItems.forEach(chat => chat.classList.remove('selected'));
                    chatItem.classList.add('selected');
                }
                
                // 更新聊天窗口
                document.querySelector('.chat-window .title').textContent = name;
                
                // 确保聊天历史存在
                if (!chatHistory[name]) {
                    chatHistory[name] = [];
                }
                
                // 更新聊天窗口内容
                updateChatWindowContent(name);
                
                // 显示聊天窗口（特别是在移动设备上）
                if (window.innerWidth <= 768) {
                    chatWindow.classList.add('active');
                }
            });
        });
    }
    
    // 初始设置联系人点击处理程序
    setupContactItemClickHandlers();

    // 返回按钮（移动设备）
    if (backBtn) {
        backBtn.addEventListener('click', function() {
            chatWindow.classList.remove('active');
        });
    }

    // 添加好友按钮
    if (addFriendBtn) {
        addFriendBtn.addEventListener('click', function() {
            addFriendModal.style.display = 'flex';
        });
    }

    // 好友管理按钮
    if (manageFriendsBtn) {
        manageFriendsBtn.addEventListener('click', function() {
            // 更新好友管理界面，确保与通讯录同步
            updateFriendManagementUI();
            manageFriendsModal.style.display = 'flex';
        });
    }

    // 关闭模态框
    closeButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            modal.style.display = 'none';
        });
    });
    
    // 将创建群组模态框的关闭按钮添加到集合中
    const createGroupModalClose = document.querySelector('#create-group-modal .close');
    if (createGroupModalClose) {
        createGroupModalClose.addEventListener('click', function() {
            createGroupModal.style.display = 'none';
        });
    }

    // 点击模态框外部关闭
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.style.display = 'none';
        }
    });

    // 标签页切换
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            
            // 更新标签状态
            tabs.forEach(t => {
                t.classList.remove('active');
            });
            this.classList.add('active');
            
            // 更新内容显示
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === tabId + '-content') {
                    content.classList.add('active');
                    
                    // 如果切换到好友请求标签页，确保绑定按钮事件
                    if (tabId === 'requests') {
                        bindFriendRequestButtons();
                    }
                }
            });
        });
    });

    // 设置按钮
    if (settingsBtn) {
        settingsBtn.addEventListener('click', function() {
            alert('设置功能开发中...');
        });
    }
    
    // 通过事件委托添加登出事件监听
    document.addEventListener('click', function(e) {
        // 检查是否点击了登出按钮或其子元素
        if (e.target.closest('.profile-item.logout') || e.target.closest('#logout-btn')) {
            if (confirm('确定要退出登录吗？')) {
                performLogout();
            }
        }
    });

    // 统一的登出函数
    function performLogout(force = false) {
        console.log('开始执行登出操作，强制模式:', force);
        
        // 显示加载状态
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'logout-loading';
        loadingIndicator.innerHTML = '<div class="loading-spinner"></div><div class="loading-text">正在退出登录...</div>';
        document.body.appendChild(loadingIndicator);
        
        const logoutUrl = force ? '/api/force_logout' : '/api/logout';
        
        fetch(logoutUrl, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin' // 确保发送cookie以维持会话
        })
        .then(response => {
            console.log('登出请求响应状态:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('登出响应数据:', data);
            if (data.success) {
                console.log(force ? '强制登出成功' : '正常登出成功');
                // 清除本地存储的用户信息
                window.currentUserId = '';
                window.allFriendsList = [];
                window.onlineFriendsList = [];
                
                // 短暂延迟后跳转到登录页面，给用户一个视觉反馈
                setTimeout(() => {
                    // 跳转到登录页面
                    window.location.href = '/login';
                }, 500);
            } else {
                if (!force) {
                    console.warn('正常登出失败，尝试强制登出');
                    // 如果正常登出失败，尝试强制登出
                    performLogout(true);
                } else {
                    console.error('强制登出也失败了:', data.message);
                    alert('登出失败: ' + (data.message || '未知错误') + '，请刷新页面重试');
                    // 即使失败也要跳转到登录页面
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 1000);
                }
            }
        })
        .catch(error => {
            console.error('登出过程中出错:', error);
            if (!force) {
                console.warn('尝试强制登出');
                performLogout(true);
            } else {
                alert('登出过程中出现错误，请刷新页面重试');
                // 即使出错也要跳转到登录页面
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1000);
            }
        })
        .finally(() => {
            // 无论成功失败，一段时间后移除加载指示器
            setTimeout(() => {
                if (document.body.contains(loadingIndicator)) {
                    document.body.removeChild(loadingIndicator);
                }
            }, 500);
        });
    }

    // 发送消息
    if (sendBtn && messageInput) {
        sendBtn.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }

    // 添加好友搜索按钮
    const searchBtn = document.querySelector('.search-btn');
    const searchResult = document.querySelector('.search-result');
    
    if (searchBtn) {
        searchBtn.addEventListener('click', function() {
            const searchInput = document.getElementById('search-friend-input');
            const searchTerm = searchInput.value.trim();
            
            if (!searchTerm) {
                searchResult.innerHTML = '<p>请输入用户名或账号</p>';
                return;
            }
            
            // 模拟搜索结果
            searchResult.innerHTML = `
                <div class="friend-item">
                    <div class="avatar">
                        ${generateAvatar(searchTerm)}
                    </div>
                    <div class="name">搜索结果: ${searchTerm}</div>
                    <div class="actions">
                        <button class="accept-btn">添加</button>
                    </div>
                </div>
            `;
        });
    }
    
    // 添加搜索结果的处理到全局点击事件处理程序
    document.addEventListener('click', function(e) {
        // 搜索结果中的添加按钮
        if (e.target.classList.contains('accept-btn') && e.target.closest('.friend-item') && e.target.closest('.search-result')) {
            const friendItem = e.target.closest('.friend-item');
            const friendName = friendItem.querySelector('.name').textContent.replace('搜索结果: ', '');
            // 发送后端请求
            const formData = new FormData();
            formData.append('friend_username', friendName);
            fetch('/api/add_friend', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                if (data.success) {
                    // 可选：自动添加到通讯录
                    addContactToList(friendName);
                }
            });
        }
    });

    // 处理好友删除和好友请求 - 统一到一个全局事件处理程序
    document.addEventListener('click', function(e) {
        // 处理删除好友按钮
        if (e.target.classList.contains('delete-btn') && e.target.closest('.friend-item')) {
            const friendItem = e.target.closest('.friend-item');
            const friendName = friendItem.querySelector('.name').textContent;
            if (confirm(`确定要删除好友 "${friendName}" 吗？`)) {
                const formData = new FormData();
                formData.append('friend_username', friendName);
                fetch('/api/remove_friend', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    if (data.success) {
                        friendItem.remove();
                        // 其他UI同步删除
                        updateFriendManagementUI();
                    }
                });
            }
        }
    });

    // 我们已经使用直接绑定替代了事件委托方式，移除这个可能导致冲突的事件处理

    // 窗口大小变化时更新界面
    window.addEventListener('resize', updateMobileView);
    
    // 添加聊天列表搜索功能
    function setupChatSearch() {
        const chatSearchInput = document.getElementById('chat-search-input');
        if (chatSearchInput) {
            // 移除之前的事件监听器
            const clone = chatSearchInput.cloneNode(true);
            chatSearchInput.parentNode.replaceChild(clone, chatSearchInput);
            
            // 添加新的事件监听器
            clone.addEventListener('input', function() {
                const searchTerm = this.value.trim().toLowerCase();
                const chatItems = document.querySelectorAll('.chat-list .chat-item');
                
                console.log("搜索聊天:", searchTerm); // 调试信息
                
                // 如果搜索框为空，显示所有聊天项
                if (searchTerm === '') {
                    chatItems.forEach(item => {
                        item.style.display = 'flex';
                    });
                    return;
                }
                
                // 过滤聊天项
                chatItems.forEach(item => {
                    const name = item.querySelector('.name').textContent.toLowerCase();
                    const message = item.querySelector('.message').textContent.toLowerCase();
                    
                    if (name.includes(searchTerm) || message.includes(searchTerm)) {
                        item.style.display = 'flex';
                    } else {
                        item.style.display = 'none';
                    }
                });
            });
        }
    }
    
    // 添加联系人搜索功能
    function setupContactSearch() {
        const contactSearchInput = document.getElementById('contact-search-input');
        if (contactSearchInput) {
            // 移除之前的事件监听器
            const clone = contactSearchInput.cloneNode(true);
            contactSearchInput.parentNode.replaceChild(clone, contactSearchInput);
            
            // 添加新的事件监听器
            clone.addEventListener('input', function() {
                const searchTerm = this.value.trim().toLowerCase();
                const contactItems = document.querySelectorAll('.contacts .contact-item');
                
                console.log("搜索联系人:", searchTerm); // 调试信息
                
                // 如果搜索框为空，显示所有联系人
                if (searchTerm === '') {
                    contactItems.forEach(item => {
                        item.style.display = 'flex';
                    });
                    return;
                }
                
                // 过滤联系人
                contactItems.forEach(item => {
                    const name = item.querySelector('.name').textContent.toLowerCase();
                    
                    if (name.includes(searchTerm)) {
                        item.style.display = 'flex';
                    } else {
                        item.style.display = 'none';
                    }
                });
            });
        }
    }
    
    // 初始设置搜索功能
    setupChatSearch();
    setupContactSearch();

    // 发送消息函数
    function sendMessage(type = 'text', content = null) {
        // 对于文本消息，使用输入框的值
        if (type === 'text') {
            content = messageInput.value.trim();
            if (!content) return;
        }
        
        // 对于图片消息，content 应该是图片的 URL 或 data URL
        if (type === 'image' && !content) return;
        
        const currentChatTitle = document.querySelector('.chat-window .title').textContent;
        const currentChatName = currentChatTitle.split(' ')[0]; // 分离群组名称和成员数
        if (!currentChatName) return;
        
        const timeString = getCurrentTime();
        
        // 添加消息到聊天历史
        if (!chatHistory[currentChatName]) {
            chatHistory[currentChatName] = [];
        }
        
        // 添加发送的消息到本地聊天历史
        chatHistory[currentChatName].push({
            type: 'sent',
            contentType: type,
            content: content,
            time: timeString
        });
        
        // 更新聊天窗口
        updateChatWindowContent(currentChatName);
        
        // 更新聊天列表中的最新消息
        const messagePreview = type === 'text' ? content : '[图片]';
        updateChatListItem(currentChatName, messagePreview, timeString);
        
        // 清空输入框（仅文本消息时）
        if (type === 'text') {
            messageInput.value = '';
        }
        
        // 检查是否是群组聊天
        const isGroup = groupChats.some(g => g.name === currentChatName);
        
        if (isGroup) {
            // 群组聊天逻辑（将来可以实现）
            console.log("群组聊天功能正在开发中...");
            
            // 向群组中的每个成员发送消息
            // TODO: 实现群组消息发送
        } else {
            // 个人聊天 - 通过Socket.IO发送真实P2P消息
            socket.emit('send_message', {
                recipient: currentChatName,
                message: content
            });
        }
    }

    // 更新移动设备视图
    function updateMobileView() {
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            chatWindow.classList.remove('active');
        }
    }
    
    // 填充联系人选择列表
    function populateContactSelection() {
        const contactSelection = document.querySelector('.contact-selection');
        contactSelection.innerHTML = '';
        
        // 获取所有联系人
        const contacts = document.querySelectorAll('.contact-item');
        
        contacts.forEach(contact => {
            const name = contact.querySelector('.name').textContent;
            
            // 创建联系人选择项
            const contactSelectItem = document.createElement('div');
            contactSelectItem.className = 'contact-select-item';
            contactSelectItem.setAttribute('data-name', name);
            contactSelectItem.innerHTML = `
                <div class="avatar">
                    ${generateAvatar(name)}
                </div>
                <div class="name">${name}</div>
                <div class="checkbox">
                    <i class="fas fa-check"></i>
                </div>
            `;
            
            // 添加点击事件
            contactSelectItem.addEventListener('click', function() {
                const isSelected = this.classList.contains('selected');
                const name = this.getAttribute('data-name');
                
                if (isSelected) {
                    // 取消选择
                    this.classList.remove('selected');
                    selectedMembers = selectedMembers.filter(member => member !== name);
                    
                    // 移除已选择标签
                    const tags = selectedMembersList.querySelectorAll('.selected-member-tag');
                    tags.forEach(tag => {
                        if (tag.getAttribute('data-name') === name) {
                            tag.remove();
                        }
                    });
                } else {
                    // 选择
                    this.classList.add('selected');
                    selectedMembers.push(name);
                    
                    // 添加已选择标签
                    const tag = document.createElement('div');
                    tag.className = 'selected-member-tag';
                    tag.setAttribute('data-name', name);
                    tag.innerHTML = `
                        ${name}
                        <span class="remove">&times;</span>
                    `;
                    
                    // 添加移除标签事件
                    tag.querySelector('.remove').addEventListener('click', function(e) {
                        e.stopPropagation();
                        
                        // 移除成员
                        selectedMembers = selectedMembers.filter(member => member !== name);
                        
                        // 更新UI
                        tag.remove();
                        document.querySelector(`.contact-select-item[data-name="${name}"]`).classList.remove('selected');
                        selectedMembersCount.textContent = selectedMembers.length;
                        
                        // 更新创建按钮状态
                        updateCreateButtonState();
                    });
                    
                    selectedMembersList.appendChild(tag);
                }
                
                // 更新已选择计数
                selectedMembersCount.textContent = selectedMembers.length;
                
                // 更新创建按钮状态
                updateCreateButtonState();
            });
            
            contactSelection.appendChild(contactSelectItem);
        });
    }
    
    // 更新创建按钮状态
    function updateCreateButtonState() {
        const groupName = groupNameInput.value.trim();
        
        if (groupName && selectedMembers.length > 0) {
            confirmCreateGroupBtn.disabled = false;
        } else {
            confirmCreateGroupBtn.disabled = true;
        }
    }
    
    // 创建群组
    function createGroup(name, members) {
        // 创建群组对象
        const group = {
            id: 'group_' + Date.now(),
            name: name,
            members: members,
            createdAt: new Date(),
            messages: [],
            isGroup: true
        };
        
        // 添加到群组列表
        groupChats.push(group);
        
        // 创建聊天项
        const chatList = document.querySelector('#chats-panel .list');
        const newChatItem = document.createElement('div');
        newChatItem.className = 'chat-item';
        newChatItem.setAttribute('data-name', name);
        newChatItem.setAttribute('data-is-group', 'true');
        newChatItem.innerHTML = `
            <div class="avatar">
                ${generateAvatar(name)}
            </div>
            <div class="content">
                <div class="name">${name}</div>
                <div class="message">群组已创建，${members.length}名成员</div>
            </div>
            <div class="time">${getCurrentTime()}</div>
        `;
        
        // 在通讯录中添加群组
        const contactsPanel = document.getElementById('contacts-panel');
        const contactsList = contactsPanel.querySelector('.list');
        
        const contactItem = document.createElement('div');
        contactItem.className = 'contact-item';
        contactItem.setAttribute('data-name', name);
        contactItem.setAttribute('data-is-group', 'true');
        
        contactItem.innerHTML = `
            <div class="avatar">${generateAvatar(name)}</div>
            <div class="name">${name} <span style="font-size: 12px; color: #666;">(群聊)</span></div>
        `;
        
        contactsList.appendChild(contactItem);
        
        // 为新聊天项添加点击事件
        newChatItem.addEventListener('click', function() {
            const chatItems = document.querySelectorAll('.chat-item');
            chatItems.forEach(chat => chat.classList.remove('selected'));
            this.classList.add('selected');
            
            const groupName = this.querySelector('.name').textContent;
            
            // 查找群组
            const group = groupChats.find(g => g.name === groupName);
            
            // 更新聊天窗口标题
            document.querySelector('.chat-window .title').textContent = `${groupName} (${group.members.length}人)`;
            
            // 初始化聊天历史
            if (!chatHistory[groupName]) {
                chatHistory[groupName] = [
                    {
                        type: 'system',
                        content: `群组 "${groupName}" 已创建`,
                        time: getCurrentTime()
                    },
                    {
                        type: 'system',
                        content: `成员：${group.members.join('、')}`,
                        time: getCurrentTime()
                    }
                ];
            }
            
            // 更新聊天窗口内容
            updateChatWindowContent(groupName);
            
            // 在移动设备上显示聊天窗口
            if (window.innerWidth <= 768) {
                chatWindow.classList.add('active');
            }
        });
        
        // 添加到聊天列表的顶部
        chatList.prepend(newChatItem);
        
        // 自动点击新创建的群组
        newChatItem.click();
        
        // 切换到消息面板
        menuItems.forEach(menuItem => {
            menuItem.classList.remove('active');
            if (menuItem.getAttribute('data-panel') === 'chats') {
                menuItem.classList.add('active');
            }
        });
        
        panels.forEach(panel => {
            panel.classList.remove('active');
            if (panel.id === 'chats-panel') {
                panel.classList.add('active');
            }
        });
        
        // 显示成功消息
        alert(`群组 "${name}" 创建成功！`);
    }

    // 更新聊天窗口内容
    function updateChatWindowContent(chatName) {
        // 设置当前聊天对象
        currentChat = chatName;
        
        // 设置聊天窗口标题
        const chatTitle = document.querySelector('.chat-window .title');
        chatTitle.textContent = chatName;
        
        // 检查是否为群聊
        const chatItem = document.querySelector(`.chat-item[data-name="${chatName}"]`);
        isCurrentChatGroup = chatItem && chatItem.getAttribute('data-is-group') === 'true';
        
        // 更新群聊相关按钮显示状态
        const groupMembersBtn = document.getElementById('group-members-btn');
        const dissolveGroupBtn = document.getElementById('dissolve-group-btn');
        const chatInfoBtn = document.getElementById('chat-info-btn');
        
        if (isCurrentChatGroup) {
            groupMembersBtn.style.display = 'inline-block';
            dissolveGroupBtn.style.display = 'inline-block';
            chatInfoBtn.style.display = 'none';
        } else {
            groupMembersBtn.style.display = 'none';
            dissolveGroupBtn.style.display = 'none';
            chatInfoBtn.style.display = 'inline-block';
        }
        
        const messagesContainer = document.querySelector('.messages');
        messagesContainer.innerHTML = '<div class="date">今天</div>';
        
        if (chatHistory[chatName]) {
            chatHistory[chatName].forEach(msg => {
                const messageElement = document.createElement('div');
                
                if (msg.type === 'system') {
                    // 系统消息
                    messageElement.className = 'message system';
                    messageElement.innerHTML = `
                        <div class="system-message">
                            ${msg.content}
                            <div class="time">${msg.time}</div>
                        </div>
                    `;
                } else if (msg.type === 'received') {
                    // 接收消息
                    messageElement.className = 'message received';
                    
                    // 根据内容类型生成不同的HTML
                    let contentHtml = '';
                    if (msg.contentType === 'image') {
                        contentHtml = `
                            <div class="image-bubble">
                                <img src="${msg.content}" alt="图片消息">
                            </div>
                        `;
                    } else if (msg.contentType === 'steg_image') {
                        contentHtml = `
                            <div class="steg-image-bubble">
                                <img src="${msg.content}" alt="隐写图片">
                                <div class="hidden-message">
                                    <div class="hidden-message-title">隐藏消息:</div>
                                    <div class="hidden-message-content">${msg.hiddenMessage || '无'}</div>
                                </div>
                                ${msg.extractedMessage ? `
                                <div class="extracted-message">
                                    <div class="extracted-message-title">从图片提取的消息:</div>
                                    <div class="extracted-message-content">${msg.extractedMessage}</div>
                                </div>` : ''}
                            </div>
                        `;
                    } else {
                        contentHtml = `<div class="bubble">${msg.content}</div>`;
                    }
                    
                    messageElement.innerHTML = `
                        <div class="avatar">
                            ${generateAvatar(msg.sender || chatName)}
                        </div>
                        <div class="content">
                            ${msg.sender ? `<div class="sender">${msg.sender}</div>` : ''}
                            ${contentHtml}
                            <div class="time">${msg.time}</div>
                        </div>
                    `;
                } else {
                    // 发送消息
                    messageElement.className = 'message sent';
                    
                    // 根据内容类型生成不同的HTML
                    let contentHtml = '';
                    if (msg.contentType === 'image') {
                        contentHtml = `
                            <div class="image-bubble">
                                <img src="${msg.content}" alt="图片消息">
                            </div>
                        `;
                    } else if (msg.contentType === 'steg_image') {
                        contentHtml = `
                            <div class="steg-image-bubble">
                                <img src="${msg.content}" alt="隐写图片">
                                <div class="hidden-message">
                                    <div class="hidden-message-title">隐藏消息:</div>
                                    <div class="hidden-message-content">${msg.hiddenMessage || '无'}</div>
                                </div>
                                ${msg.extractedMessage ? `
                                <div class="extracted-message">
                                    <div class="extracted-message-title">从图片提取的消息:</div>
                                    <div class="extracted-message-content">${msg.extractedMessage}</div>
                                </div>` : ''}
                            </div>
                        `;
                    } else {
                        contentHtml = `<div class="bubble">${msg.content}</div>`;
                    }
                    
                    messageElement.innerHTML = `
                        <div class="content">
                            ${contentHtml}
                            <div class="time">${msg.time}</div>
                        </div>
                    `;
                }
                
                messagesContainer.appendChild(messageElement);
            });
        }
        
        // 滚动到底部
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // 移除新消息标记
        const chatItems = document.querySelectorAll('.chat-item');
        chatItems.forEach(item => {
            const itemName = item.querySelector('.name').textContent.trim();
            if (itemName === chatName) {
                item.classList.remove('new-message');
            }
        });
    }

    // 更新聊天列表项
    function updateChatListItem(name, message, time) {
        const chatList = document.querySelector('.chat-list .list');
        const chatItems = chatList.querySelectorAll('.chat-item');
        let chatItem = null;
        
        for (let i = 0; i < chatItems.length; i++) {
            if (chatItems[i].querySelector('.name').textContent === name) {
                chatItem = chatItems[i];
                break;
            }
        }
        
        if (chatItem) {
            chatItem.querySelector('.message').textContent = message;
            chatItem.querySelector('.time').textContent = time;
            
            // 将该聊天项移到顶部
            chatList.prepend(chatItem);
        }
    }

    // 获取当前时间
    function getCurrentTime() {
        const now = new Date();
        const hours = now.getHours();
        const minutes = now.getMinutes() < 10 ? '0' + now.getMinutes() : now.getMinutes();
        return hours + ':' + minutes;
    }

    // 更新好友管理界面，确保与通讯录同步
    function updateFriendManagementUI() {
        const contactItems = document.querySelectorAll('.contact-item');
        const friendsContent = document.getElementById('all-friends-content');
        
        // 清空现有内容
        friendsContent.innerHTML = '';
        
        // 从通讯录填充好友管理界面
        contactItems.forEach(item => {
            const name = item.querySelector('.name').textContent;
            
            const friendItem = document.createElement('div');
            friendItem.className = 'friend-item';
            friendItem.innerHTML = `
                <div class="avatar">
                    ${generateAvatar(name)}
                </div>
                <div class="name">${name}</div>
                <div class="actions">
                    <button class="delete-btn">删除</button>
                </div>
            `;
            
            friendsContent.appendChild(friendItem);
        });
    }
    
    // 重新绑定所有事件处理程序的函数
    function rebindAllEventHandlers() {
        // 重新绑定聊天项点击事件
        setupChatItemClickHandlers();
        
        // 重新绑定联系人点击事件
        setupContactItemClickHandlers();
        
        // 重新绑定好友请求按钮事件
        bindFriendRequestButtons();
        
        // 重新设置搜索功能
        setupChatSearch();
        setupContactSearch();
    }

    // 安全处理好友数据，防止因状态变化导致渲染错误
    function safeGetFriendData(friend) {
        try {
            // 基础验证
            if (!friend) return null;
            
            // 提取基本信息，设置默认值
            const name = friend.username || friend.name || '';
            if (!name) return null; // 没有用户名则视为无效数据
            
            // 规范化字段名，返回清理后的数据对象
            return {
                username: name,
                user_id: friend.user_id || friend.UserID || '',
                ip_address: friend.ip_address || friend.IPAddress || friend.ip || '',
                p2p_port: friend.p2p_port || friend.P2PPort || friend.port || 0,
                public_key: friend.public_key || ''
            };
        } catch (error) {
            console.error('处理好友数据时出错:', error);
            return null; // 出错时返回null，便于过滤
        }
    }

    // 渲染通讯录
    function renderContacts() {
        try {
            const contactList = document.querySelector('.contacts .list');
            if (!contactList) return; // 如果找不到容器，直接返回
            
            contactList.innerHTML = '';
            
            // 确保全局数据已初始化为数组
            if (!window.onlineFriendsList || !Array.isArray(window.onlineFriendsList)) {
                window.onlineFriendsList = [];
            }
            
            if (!window.allFriendsList || !Array.isArray(window.allFriendsList)) {
                window.allFriendsList = [];
            }
            
            // 检查好友列表是否为空
            if (window.allFriendsList.length === 0) {
                contactList.innerHTML = '<div class="empty-contacts-message">您的通讯录为空，快去添加好友吧！</div>';
                return;
            }
            
            // 创建安全的好友数据 - 根据全部好友列表渲染通讯录
            const safeAllFriends = window.allFriendsList
                .map(safeGetFriendData)
                .filter(friend => friend !== null);
                
            // 创建安全的在线好友数据 - 用于标记在线状态
            const safeOnlineFriends = window.onlineFriendsList
                .map(safeGetFriendData)
                .filter(friend => friend !== null);
                
            // 创建在线用户名集合，便于快速查询
            const onlineUsernames = new Set(safeOnlineFriends.map(f => f.username));
            
            // 按在线状态排序：在线好友优先显示
            const sortedFriends = [...safeAllFriends].sort((a, b) => {
                const aIsOnline = onlineUsernames.has(a.username);
                const bIsOnline = onlineUsernames.has(b.username);
                return bIsOnline - aIsOnline; // 在线的排在前面
            });
            
            // 如果处理后的好友列表为空，显示适当的消息
            if (sortedFriends.length === 0) {
                contactList.innerHTML = '<div class="empty-contacts-message">没有找到有效的好友数据</div>';
                return;
            }
            
            // 渲染每个好友
            sortedFriends.forEach(friend => {
                const name = friend.username;
                const isOnline = onlineUsernames.has(name);
                
                // 收集要显示的详细信息
                const details = [];
                if (friend.user_id) details.push('ID: ' + friend.user_id);
                
                // 只有当好友在线时才查找并显示IP和端口
                if (isOnline) {
                    const onlineFriend = safeOnlineFriends.find(f => f.username === name);
                    if (onlineFriend) {
                        if (onlineFriend.ip_address) details.push('IP: ' + onlineFriend.ip_address);
                        if (onlineFriend.p2p_port) details.push('P2P端口: ' + onlineFriend.p2p_port);
                    }
                }
                
                // 创建联系人项
                const newContact = document.createElement('div');
                newContact.className = 'contact-item';
                newContact.setAttribute('data-name', name);
                newContact.setAttribute('data-user-id', friend.user_id || '');
                newContact.classList.add(isOnline ? 'online' : 'offline');
                
                // 设置联系人项的HTML内容
                newContact.innerHTML = `
                    <div class="avatar">${generateAvatar(name)}</div>
                    <div class="name">${name} ${isOnline ? '<span class="status-indicator online"></span>' : '<span class="status-indicator offline"></span>'}</div>
                    ${details.length > 0 ? `<div class="details">${details.join(' | ')}</div>` : ''}
                    <div class="contact-actions">
                        <button class="chat-btn" title="发起聊天"><i class="fas fa-comment"></i></button>
                        ${isOnline ? '<span class="online-badge">在线</span>' : '<span class="offline-badge">离线</span>'}
                    </div>
                `;
                
                contactList.appendChild(newContact);
            });
            
            // 绑定事件处理程序
            setupContactItemClickHandlers();
            
            // 绑定聊天按钮点击事件
            document.querySelectorAll('.contact-item .chat-btn').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation(); // 阻止事件冒泡，防止触发联系人项的点击事件
                    const contactItem = this.closest('.contact-item');
                    simulateContactItemClick(contactItem);
                });
            });
        } catch (error) {
            console.error('渲染通讯录时出错:', error);
            // 在出错时显示友好的错误信息
            const contactList = document.querySelector('.contacts .list');
            if (contactList) {
                contactList.innerHTML = '<div class="error-message">渲染通讯录时出错，请刷新页面重试</div>';
                
                // 添加重试按钮
                const retryButton = document.createElement('button');
                retryButton.className = 'retry-btn';
                retryButton.textContent = '重试';
                retryButton.addEventListener('click', function() {
                    // 模拟点击"通讯录"菜单项以刷新
                    const contactsMenuItem = document.querySelector('[data-panel="contacts"]');
                    if (contactsMenuItem) {
                        contactsMenuItem.click();
                    }
                });
                contactList.appendChild(retryButton);
            }
        }
    }
    
    // 辅助函数：模拟联系人项的点击
    function simulateContactItemClick(contactItem) {
        try {
            const name = contactItem.getAttribute('data-name');
            if (!name) return;
            
            console.log("发起与联系人的聊天：", name);
            
            // 切换到消息面板
            menuItems.forEach(menuItem => {
                menuItem.classList.remove('active');
                if (menuItem.getAttribute('data-panel') === 'chats') {
                    menuItem.classList.add('active');
                }
            });
            
            panels.forEach(panel => {
                panel.classList.remove('active');
                if (panel.id === 'chats-panel') {
                    panel.classList.add('active');
                }
            });
            
            // 查找或创建与该联系人的聊天项
            let chatItem = null;
            const existingChatItems = document.querySelectorAll('.chat-item');
            
            for (let i = 0; i < existingChatItems.length; i++) {
                const itemName = existingChatItems[i].querySelector('.name').textContent.trim();
                if (itemName === name) {
                    chatItem = existingChatItems[i];
                    break;
                }
            }
            
            // 获取在线状态
            const isOnline = contactItem.classList.contains('online');
            
            // 如果找不到现有聊天，创建一个新的聊天项
            if (!chatItem) {
                const chatList = document.querySelector('.chat-list .list');
                if (!chatList) {
                    console.error("无法找到聊天列表容器");
                    return;
                }
                
                chatItem = document.createElement('div');
                chatItem.className = 'chat-item';
                chatItem.innerHTML = `
                    <div class="avatar">${generateAvatar(name)}</div>
                    <div class="content">
                        <div class="name">${name} 
                            ${isOnline ? 
                            '<span class="status-indicator online"></span>' : 
                            '<span class="status-indicator offline"></span>'}
                        </div>
                        <div class="message">点击开始聊天</div>
                    </div>
                    <div class="time">${getCurrentTime()}</div>
                `;
                chatList.prepend(chatItem);
                setupChatItemClickHandlers();
            }
            
            // 触发聊天项的点击事件
            if (chatItem) {
                chatItem.click();
            }
        } catch (error) {
            console.error("模拟联系人点击时出错:", error);
        }
    }
    
    // 修改addContactToList：只添加联系人项，不切换聊天面板
    function addContactToList(name, isOnline = false) {
        const contactList = document.querySelector('.contacts .list');
        if (name.includes('搜索结果:')) name = name.replace('搜索结果: ', '');
        // 检查是否已存在
        const existingContacts = contactList.querySelectorAll('.contact-item');
        for (let i = 0; i < existingContacts.length; i++) {
            if (existingContacts[i].querySelector('.name').textContent === name) return;
        }
        const newContact = document.createElement('div');
        newContact.className = 'contact-item';
        newContact.innerHTML = `
            <div class="avatar">${generateAvatar(name)}</div>
            <div class="name">${name} ${isOnline ? '<span class="status-indicator online"></span>' : '<span class="status-indicator offline"></span>'}</div>
        `;
        contactList.appendChild(newContact);
        setupContactItemClickHandlers();
    }

    // 辅助函数: jQuery-like contains 选择器
    Element.prototype.contains = function(text) {
        return this.textContent.includes(text);
    };
    
    // 绑定好友请求按钮的点击事件
    function bindFriendRequestButtons() {
        document.querySelectorAll('.request-item .accept-btn').forEach(btn => {
            if (!btn.hasAttribute('data-bound')) {
                btn.setAttribute('data-bound', 'true');
                btn.onclick = function() {
                    const requestItem = this.closest('.request-item');
                    const friendName = requestItem.querySelector('.name').textContent;
                    
                    console.log("接受好友请求:", friendName);
                    
                    // 添加到通讯录
                    addContactToList(friendName, true); // 假设接受的好友请求是来自在线用户
                    
                    // 提示成功
                    alert(`已接受 ${friendName} 的好友请求`);
                    
                    // 移除请求项
                    requestItem.remove();
                    
                    // 更新好友管理界面
                    updateFriendManagementUI();
                };
            }
        });
        
        document.querySelectorAll('.request-item .reject-btn').forEach(btn => {
            if (!btn.hasAttribute('data-bound')) {
                btn.setAttribute('data-bound', 'true');
                btn.onclick = function() {
                    const requestItem = this.closest('.request-item');
                    alert('已拒绝好友请求');
                    requestItem.remove();
                };
            }
        });
    }
    
    // 初始绑定
    bindFriendRequestButtons();
    
    // 绑定发送按钮点击事件
    if (sendBtn) {
        sendBtn.addEventListener('click', function() {
            sendMessage('text');
        });
    }
    
    // 绑定输入框按下回车键事件
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage('text');
            }
        });
    }
    
    // 表情选择器相关事件
    if (emojiPickerBtn) {
        emojiPickerBtn.addEventListener('click', function() {
            emojiPickerModal.style.display = 'flex';
        });
    }
    
    // 绑定表情点击事件
    if (emojis) {
        emojis.forEach(emoji => {
            emoji.addEventListener('click', function() {
                // 获取表情符号
                const emojiChar = this.getAttribute('data-emoji');
                
                // 将表情添加到输入框
                messageInput.value += emojiChar;
                
                // 关闭表情选择器
                emojiPickerModal.style.display = 'none';
                
                // 让输入框获取焦点
                messageInput.focus();
            });
        });
    }
    
    // 图片上传相关事件
    if (imageUploadBtn) {
        imageUploadBtn.addEventListener('click', function() {
            imageUploadInput.click();
        });
    }
    
    // 图片选择处理
    if (imageUploadInput) {
        imageUploadInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                if (!file.type.match('image.*')) {
                    alert('请选择图片文件！');
                    return;
                }
                
                const recipient = document.querySelector('.chat-window .title').textContent;
                const hiddenMsg = prompt('请输入要隐藏的消息：');
                if (!hiddenMsg) {
                    alert('请输入要隐藏的消息！');
                    return;
                }
                
                // 显示发送状态
                const messagesContainer = document.querySelector('.messages');
                const statusMsg = document.createElement('div');
                statusMsg.className = 'message system';
                statusMsg.innerHTML = `
                    <div class="system-message">
                        正在发送隐写图片...
                        <div class="time">${getCurrentTime()}</div>
                    </div>
                `;
                messagesContainer.appendChild(statusMsg);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                
                // 创建FormData对象
                const formData = new FormData();
                formData.append('recipient_username', recipient);
                formData.append('hidden_message', hiddenMsg);
                formData.append('image_file', file);
                
                // 发送隐写图片
                fetch('/api/send_steg_image', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    // 移除状态消息
                    messagesContainer.removeChild(statusMsg);
                    
                    if (data.success) {
                        // 记录发送的隐写图片到聊天历史
                        const timeString = getCurrentTime();
                        
                        // 显示图片预览（稍后会被替换为服务器处理后的图片）
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            const imgDataUrl = e.target.result;
                            
                            // 添加到聊天历史
                            if (!chatHistory[recipient]) {
                                chatHistory[recipient] = [];
                            }
                            
                            chatHistory[recipient].push({
                                type: 'sent',
                                contentType: 'steg_image',
                                content: imgDataUrl,
                                hiddenMessage: hiddenMsg,
                                time: timeString
                            });
                            
                            // 更新聊天窗口
                            updateChatWindowContent(recipient);
                            
                            // 更新聊天列表中的最新消息
                            updateChatListItem(recipient, '[隐写图片]', timeString);
                        };
                        reader.readAsDataURL(file);
                    } else {
                        // 显示错误消息
                        const errorMsg = document.createElement('div');
                        errorMsg.className = 'message system';
                        errorMsg.innerHTML = `
                            <div class="system-message error">
                                隐写图片发送失败：${data.message}
                                <div class="time">${getCurrentTime()}</div>
                            </div>
                        `;
                        messagesContainer.appendChild(errorMsg);
                        messagesContainer.scrollTop = messagesContainer.scrollHeight;
                    }
                })
                .catch(error => {
                    // 移除状态消息
                    messagesContainer.removeChild(statusMsg);
                    
                    // 显示错误消息
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'message system';
                    errorMsg.innerHTML = `
                        <div class="system-message error">
                            隐写图片发送失败：网络错误
                            <div class="time">${getCurrentTime()}</div>
                        </div>
                    `;
                    messagesContainer.appendChild(errorMsg);
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                });
                
                // 重置文件输入
                this.value = '';
            }
        });
    }
    
    // 关闭表情选择器
    document.querySelector('#emoji-picker-modal .close').addEventListener('click', function() {
        emojiPickerModal.style.display = 'none';
    });
    
    // 点击模态框外部关闭表情选择器
    window.addEventListener('click', function(e) {
        if (e.target === emojiPickerModal) {
            emojiPickerModal.style.display = 'none';
        }
    });
    
    // 监视DOM变化，为新添加的好友请求按钮绑定事件
    const observer = new MutationObserver(function(mutations) {
        bindFriendRequestButtons();
    });
    
    const requestsContent = document.getElementById('requests-content');
    if (requestsContent) {
        observer.observe(requestsContent, { childList: true, subtree: true });
    }
    
    // 页面卸载时的清理工作
    // 完全移除页面卸载时的自动登出，只在手动点击登出按钮时执行登出
    // 这样可以彻底避免重复登出请求的问题
    window.addEventListener('beforeunload', function(e) {
        console.log('页面即将卸载，执行清理工作');
        
        // 只断开 SocketIO 连接，不发送登出请求
        if (socket) {
            socket.disconnect();
        }
    });

    const socket = io();
    
    // 处理接收到的消息
    socket.on('receive_message', function(data) {
        console.log('收到消息:', data);
        
        try {
            const sender = data.sender;
            const message = data.message;
            const time = getCurrentTime();
            
            // 如果是来自自己的消息（例如从其他设备发送的），则不处理
            if (sender === '我') {
                return;
            }
            
            // 检查是否已有此发送者的聊天历史
            if (!chatHistory[sender]) {
                chatHistory[sender] = [];
                
                // 如果聊天列表中没有此联系人，添加一个
                const chatList = document.querySelector('.chat-list .list');
                if (!chatList) return;
                
                const existingChatItems = chatList.querySelectorAll('.chat-item');
                let exists = false;
                
                for (let i = 0; i < existingChatItems.length; i++) {
                    const itemName = existingChatItems[i].querySelector('.name').textContent.trim();
                    if (itemName === sender) {
                        exists = true;
                        break;
                    }
                }
                
                if (!exists) {
                    // 安全地确定好友是否在线
                    let isOnline = false;
                    
                    if (window.onlineFriendsList && Array.isArray(window.onlineFriendsList)) {
                        isOnline = window.onlineFriendsList.some(f => {
                            if (!f) return false;
                            return (f.username === sender || f.name === sender);
                        });
                    }
                    
                    const newChatItem = document.createElement('div');
                    newChatItem.className = 'chat-item';
                    newChatItem.setAttribute('data-name', sender);
                    newChatItem.innerHTML = `
                        <div class="avatar">${generateAvatar(sender)}</div>
                        <div class="content">
                            <div class="name">${sender} ${isOnline ? '<span class="status-indicator online"></span>' : '<span class="status-indicator offline"></span>'}</div>
                            <div class="message">${message}</div>
                        </div>
                        <div class="time">${time}</div>
                    `;
                    
                    chatList.prepend(newChatItem);
                    setupChatItemClickHandlers();
                }
            }
            
            // 添加消息到聊天历史
            chatHistory[sender].push({
                type: 'received',
                contentType: 'text',
                content: message,
                time: time
            });
            
            // 更新聊天列表项
            updateChatListItem(sender, message, time);
            
            // 如果当前正在查看此聊天，则更新聊天窗口
            if (currentChat === sender) {
                updateChatWindowContent(sender);
            } else {
                // 显示新消息通知
                const notification = `新消息: ${sender} - ${message}`;
                
                // 如果浏览器支持通知API，并且用户已授权，则显示桌面通知
                if ("Notification" in window && Notification.permission === "granted") {
                    new Notification("新消息", {
                        body: `${sender}: ${message}`,
                        icon: "/static/img/chat.svg"
                    });
                } else if ("Notification" in window && Notification.permission !== "denied") {
                    // 请求通知权限
                    Notification.requestPermission().then(permission => {
                        if (permission === "granted") {
                            new Notification("新消息", {
                                body: `${sender}: ${message}`,
                                icon: "/static/img/chat.svg"
                            });
                        }
                    });
                }
                
                // 高亮显示有新消息的聊天项
                const chatItems = document.querySelectorAll('.chat-item');
                chatItems.forEach(item => {
                    const itemName = item.querySelector('.name').textContent.trim();
                    if (itemName === sender) {
                        item.classList.add('new-message');
                    }
                });
            }
        } catch (error) {
            console.error('处理接收消息时出错:', error, data);
        }
    });
    
    // 处理接收到的隐写图片消息
    socket.on('receive_steg_image', function(data) {
        console.log('收到隐写图片:', data);
        
        try {
            const sender = data.sender;
            const hiddenMessage = data.hidden_message;
            const imageUrl = data.image_url;
            const extractedMessage = data.extracted_from_image;
            const time = getCurrentTime();
            
            // 检查是否已有此发送者的聊天历史
            if (!chatHistory[sender]) {
                chatHistory[sender] = [];
            }
            
            // 添加图片消息到聊天历史
            chatHistory[sender].push({
                type: 'received',
                contentType: 'steg_image',
                content: imageUrl,
                hiddenMessage: hiddenMessage,
                extractedMessage: extractedMessage,
                time: time
            });
            
            // 更新聊天列表项
            updateChatListItem(sender, '[隐写图片]', time);
            
            // 如果当前正在查看此聊天，则更新聊天窗口
            if (currentChat === sender) {
                updateChatWindowContent(sender);
            } else {
                // 显示新消息通知
                if ("Notification" in window && Notification.permission === "granted") {
                    new Notification("收到隐写图片", {
                        body: `${sender} 向你发送了一张隐写图片`,
                        icon: "/static/img/chat.svg"
                    });
                }
                
                // 高亮显示有新消息的聊天项
                const chatItems = document.querySelectorAll('.chat-item');
                chatItems.forEach(item => {
                    const itemName = item.querySelector('.name').textContent.trim();
                    if (itemName === sender) {
                        item.classList.add('new-message');
                    }
                });
            }
        } catch (error) {
            console.error('处理接收隐写图片时出错:', error, data);
        }
    });
    
    // 处理好友添加通知
    socket.on('friend_added', function(data) {
        console.log('收到好友添加通知:', data);
        
        try {
            // 显示通知消息
            if (data.message) {
                alert(data.message);
            } else {
                alert('你有一个新好友：' + data.friend);
            }
            
            // 获取当前用户ID
            const userId = window.currentUserId || '';
            
            if (!userId) {
                console.error('无法获取当前用户ID，无法刷新好友列表');
                return;
            }
            
            console.log('使用用户ID刷新好友列表:', userId, '类型:', typeof userId);
            
            // 主动向后端请求最新好友列表
            fetch('/api/refresh_friends', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userId }),
                credentials: 'same-origin' // 确保发送cookie以维持会话
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('获取好友列表失败');
                }
                return response.json();
            })
            .then(data => {
                console.log('收到服务器响应:', data);
                if (data.success) {
                    // 更新好友列表数据
                    window.onlineFriendsList = Array.isArray(data.online_friends) ? data.online_friends : [];
                    window.allFriendsList = Array.isArray(data.all_friends) ? data.all_friends : [];
                    
                    console.log('成功获取好友列表，在线好友:', window.onlineFriendsList.length, '所有好友:', window.allFriendsList.length);
                    
                    // 如果当前在通讯录页面，重新渲染
                    const contactsPanel = document.getElementById('contacts-panel');
                    if (contactsPanel && contactsPanel.classList.contains('active')) {
                        renderContacts();
                    }
                } else {
                    console.error('获取好友列表失败:', data.message);
                    // 显示错误通知，但不阻断用户操作
                    const errorMsg = data.message || '获取好友列表失败';
                    const notification = document.createElement('div');
                    notification.className = 'error-notification';
                    notification.textContent = errorMsg;
                    document.body.appendChild(notification);
                    
                    // 3秒后自动消失
                    setTimeout(() => {
                        notification.remove();
                    }, 3000);
                }
            })
            .catch(error => {
                console.error('获取最新好友列表失败:', error);
            });
        } catch (error) {
            console.error('处理好友添加通知时出错:', error, data);
        }
    });
    
    // 处理在线好友列表更新
    socket.on('refresh_online_friends', function() {
        try {
            console.log('收到好友状态变更通知，正在刷新在线好友列表');
            
            // 获取当前用户ID
            const userId = window.currentUserId || '';
            
            if (!userId) {
                console.error('无法获取当前用户ID，无法刷新好友列表');
                return;
            }
            
            console.log('使用用户ID刷新好友列表:', userId, '类型:', typeof userId);
            
            // 主动请求最新的在线好友列表
            fetch('/api/refresh_friends', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userId }),
                credentials: 'same-origin' // 确保发送cookie以维持会话
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('获取好友列表失败');
                }
                return response.json();
            })
            .then(data => {
                console.log('收到服务器响应:', data);
                if (data.success) {
                    // 更新好友列表数据
                    window.onlineFriendsList = Array.isArray(data.online_friends) ? data.online_friends : [];
                    window.allFriendsList = Array.isArray(data.all_friends) ? data.all_friends : [];
                    
                    console.log('成功获取好友列表，在线好友:', window.onlineFriendsList.length, '所有好友:', window.allFriendsList.length);
                    
                    // 如果当前在通讯录页面，重新渲染
                    const contactsPanel = document.getElementById('contacts-panel');
                    if (contactsPanel && contactsPanel.classList.contains('active')) {
                        renderContacts();
                    }
                    
                    // 更新聊天列表中好友的在线状态
                    updateChatListFriendStatus();
                } else {
                    console.error('获取好友列表失败:', data.message);
                    // 显示错误通知，但不阻断用户操作
                    const errorMsg = data.message || '获取好友列表失败';
                    const notification = document.createElement('div');
                    notification.className = 'error-notification';
                    notification.textContent = errorMsg;
                    document.body.appendChild(notification);
                    
                    // 3秒后自动消失
                    setTimeout(() => {
                        notification.remove();
                    }, 3000);
                }
            })
            .catch(error => {
                console.error('获取最新好友列表失败:', error);
            });
        } catch (error) {
            console.error('处理好友状态变更通知时出错:', error);
        }
    });
    
    // 更新聊天列表中好友的在线状态
    function updateChatListFriendStatus() {
        try {
            // 验证数据
            if (!window.onlineFriendsList || !Array.isArray(window.onlineFriendsList)) {
                return;
            }
            
            // 创建在线用户名集合
            const onlineUsernames = new Set();
            window.onlineFriendsList.forEach(friend => {
                if (friend && friend.username) {
                    onlineUsernames.add(friend.username);
                }
            });
            
            // 更新所有聊天项的在线状态
            const chatItems = document.querySelectorAll('.chat-item');
            chatItems.forEach(item => {
                const nameElement = item.querySelector('.name');
                if (!nameElement) return;
                
                const nameText = nameElement.textContent.trim();
                const isOnline = onlineUsernames.has(nameText);
                
                // 更新聊天项的在线/离线样式
                if (isOnline) {
                    item.classList.add('online');
                    item.classList.remove('offline');
                } else {
                    item.classList.add('offline');
                    item.classList.remove('online');
                }
                
                // 移除旧的状态指示器
                const oldIndicator = nameElement.querySelector('.status-indicator');
                if (oldIndicator) {
                    oldIndicator.remove();
                }
                
                // 添加新的状态指示器
                const statusIndicator = document.createElement('span');
                statusIndicator.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
                nameElement.appendChild(statusIndicator);
            });
        } catch (error) {
            console.error('更新聊天列表好友状态时出错:', error);
        }
    }

}); 