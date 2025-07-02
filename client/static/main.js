// 全局变量声明 - 确保这些变量在全局范围内可访问
let currentUserId = null;
let currentChat = null;
let socket = null;
let isCurrentChatGroup = false;
let onlineFriendsList = [];
let allFriendsList = [];
let chatHistory = {};
let activeModal = null; // 跟踪当前激活的模态框
    
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
    if (!name) name = "用户";
        const bgColor = generateAvatarColor(name);
        const initial = name.charAt(0).toUpperCase();
        
        return `
            <div class="avatar-circle" style="background-color: ${bgColor};">
                <span class="avatar-initial">${initial}</span>
            </div>
        `;
    }

document.addEventListener('DOMContentLoaded', function() {
    // Socket.IO初始化
    socket = io();
    
    // Socket.IO连接事件处理
    socket.on('connect', function() {
        console.log('Socket.IO连接已建立, ID:', socket.id);
        createConnectionStatusIndicator();
        updateConnectionStatus();
    });
    
    socket.on('disconnect', function() {
        console.log('Socket.IO连接已断开');
        updateConnectionStatus();
    });
    
    socket.on('connect_error', function(error) {
        console.error('Socket.IO连接错误:', error);
        updateConnectionStatus();
    });
    
    // 接收消息事件处理 - 确保正确处理双向通信
    socket.on('receive_message', function(data) {
        console.log('收到Socket.IO receive_message事件，原始数据:', data);
        
        // 确保数据格式正确
        if (!data) {
            console.error('接收到的消息数据为空');
            return;
        }
        
        // 兼容不同的数据格式
        const messageData = {
            sender: data.sender || data.username || data.user || '',
            recipient: data.recipient || data.to || '',
            content: data.content || data.message || data.text || '',
            time: data.time || getCurrentTime()
        };
        
        console.log('处理后的消息数据:', messageData, '当前用户ID:', currentUserId);
        
        // 处理消息 - 根据是否为自己发送来决定显示方式
        if (messageData.sender && messageData.content) {
            // 判断是否为自己发送的消息
            const isSentByMe = messageData.sender.toString() === currentUserId.toString();
            
            console.log('是否为自己发送:', isSentByMe, 
                       '发送方:', messageData.sender, 
                       '当前用户:', currentUserId,
                       '接收方:', messageData.recipient);
            
            // 如果是自己发送的消息或者是发给自己的消息，则显示
            // 确保都转为字符串进行比较，因为ID有可能是数字或字符串
            console.log(currentUserId.toString())
            if (isSentByMe || messageData.recipient.toString() === currentUserId.toString()) {
                receiveMessage(messageData, isSentByMe);
            } else {
                console.log('消息与当前用户无关，不显示');
            }
        } else {
            console.error('处理后的消息数据格式仍然不正确:', messageData);
        }
    });
    
    // 好友状态变更事件处理
    socket.on('friend_status_change', function(data) {
        console.log('好友状态变化:', data);
        updateFriendStatus(data.username, data.status);
        fetchFriendsList(); // 刷新好友列表
    });
    
    // 添加好友请求事件处理
    socket.on('friend_request', function(data) {
        console.log('收到好友请求:', data);
        showFriendRequestNotification(data);
        fetchFriendsList(); // 刷新好友列表
    });
    
    // 接收到添加好友结果事件
    socket.on('add_friend_result', function(data) {
        console.log('添加好友结果:', data);
        if(data.success) {
            showSuccessMessage(`成功添加好友：${data.friend_username}`);
            fetchFriendsList(); // 刷新好友列表
        } else {
            showErrorMessage(`添加好友失败：${data.message}`);
        }
    });

    // ... existing code ...

    // 添加模态框外部点击事件，用于关闭模态框
    // 注意：不处理#add-friend-modal和#info-modal，因为它们有自己的处理逻辑
    window.addEventListener('click', function(event) {
        // 如果点击事件已被处理，则不再处理
        if (event.defaultPrevented) {
            return;
        }
        
        // 排除特定模态框
        const modals = document.querySelectorAll('.modal:not(#add-friend-modal):not(#info-modal)');
        modals.forEach(function(modal) {
            if (modal.style.display === 'flex' && event.target === modal) {
                // 获取模态框ID
                const modalId = modal.id;
                if (modalId) {
                    event.preventDefault(); // 标记事件已被处理
                    console.log(`通过全局点击事件关闭模态框: ${modalId}`);
                    closeModal(modalId);
                }
            }
        });
    });
    
    // 添加好友按钮点击事件绑定
    const addFriendBtn = document.getElementById('add-friend-btn');
    if (addFriendBtn) {
        console.log('找到添加好友按钮，正在绑定点击事件');
        
        // 移除可能已存在的事件监听器
        addFriendBtn.removeEventListener('click', addFriendBtnHandler);
        
        // 添加新的事件监听器
        addFriendBtn.addEventListener('click', addFriendBtnHandler);
    } else {
        console.error('未找到添加好友按钮元素 (id="add-friend-btn")');
    }
    
    // 获取当前用户ID
    fetch('/api/get_current_user')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentUserId = data.user_id.toString(); // 确保ID为字符串
            console.log('已获取当前用户ID:', currentUserId);
            
            // 初始化好友列表（确保用户ID获取后再加载好友列表）
            fetchFriendsList();
        } else {
            console.error('获取当前用户ID失败:', data.message || '未知错误');
        }
    })
    .catch(error => {
        console.error('获取当前用户ID失败:', error);
    });

    // ... existing code ...

    // 获取好友列表函数
    function fetchFriendsList() {
        console.log('正在获取好友列表...');
        
        // 即使没有用户ID也尝试获取好友列表
        if (!currentUserId) {
            console.warn('警告：用户ID未设置，尝试从会话中获取');
        }
        
        // 创建要发送的数据，如果有用户ID则包含它
        const postData = currentUserId ? { user_id: currentUserId } : {};
        
        return fetch('/api/refresh_friends', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(postData),
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP错误! 状态: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                let friends = Array.isArray(data.online_friends) ? data.online_friends : [];
                let all = Array.isArray(data.all_friends) ? data.all_friends : [];
                
                console.log(`刷新好友列表成功，在线好友: ${friends.length}, 所有好友: ${all.length}`);
                console.log('在线好友:', friends);
                console.log('所有好友:', all);
                
                // 处理可能的错误格式
                friends = friends.filter(friend => friend && (typeof friend === 'string' || friend.username));
                all = all.filter(friend => friend && (typeof friend === 'string' || friend.username));
                
                // 更新全局好友列表
                onlineFriendsList = friends;
                allFriendsList = all;
                
                // 记录从localStorage加载聊天历史
                try {
                    const storedHistory = localStorage.getItem('chatHistory');
                    if (storedHistory) {
                        console.log('从localStorage加载聊天历史');
                        chatHistory = JSON.parse(storedHistory) || {};
                    }
                } catch (e) {
                    console.error('加载聊天历史出错:', e);
                    chatHistory = {};
                }
                
                // 重新渲染联系人和聊天列表
                try {
                    renderContacts();
                } catch (err) {
                    console.error('渲染联系人时出错:', err);
                }
                
                try {
                    if (typeof updateChatListFriendStatus === 'function') {
                        updateChatListFriendStatus();
                    } else {
                        console.warn('updateChatListFriendStatus 函数未定义');
                    }
                } catch (err) {
                    console.error('更新聊天列表状态时出错:', err);
                }
                
                console.log('已更新全局好友列表');
                return {friends, all};
            } else {
                console.error('刷新好友列表失败:', data.message);
                
                // 即使API调用失败，也尝试用空列表渲染UI
                onlineFriendsList = [];
                allFriendsList = [];
                renderContacts();
                
                throw new Error(data.message || '刷新好友列表失败');
            }
        })
        .catch(error => {
            console.error('获取初始好友列表出错:', error);
            
            // 出错时也尝试用空列表渲染UI
            onlineFriendsList = [];
            allFriendsList = [];
            renderContacts();
            
            throw error;
        });
    }

    // ... existing code ...

    // 渲染联系人列表函数的修改
    function renderContacts() {
        try {
            console.log('开始渲染联系人列表...');
            
            const contactsContainer = document.querySelector('.contacts .list');
            if (!contactsContainer) {
                console.error('找不到联系人容器元素 .contacts .list');
                return;
            }
    
            // 清空当前联系人列表
            contactsContainer.innerHTML = '';
            
            console.log('联系人数据:', {
                onlineFriends: onlineFriendsList ? onlineFriendsList.length : '未定义',
                allFriends: allFriendsList ? allFriendsList.length : '未定义'
            });
            
            // 确保列表是数组，即使是空数组也可以
            const onlineFriends = Array.isArray(onlineFriendsList) ? onlineFriendsList : [];
            const allFriends = Array.isArray(allFriendsList) ? allFriendsList : [];
    
            // 添加在线好友
            const onlineHeader = document.createElement('div');
            onlineHeader.className = 'contacts-category';
            onlineHeader.textContent = `在线好友 (${onlineFriends.length})`;
            contactsContainer.appendChild(onlineHeader);
            
            if (onlineFriends.length > 0) {
                onlineFriends.forEach(friend => {
                    try {
                        const friendName = friend.username || friend;
                        if (friendName) {
                            addContactToList(friendName, true);
                    } else {
                            console.warn('在线好友数据无效:', friend);
                        }
                    } catch (err) {
                        console.error('处理在线好友时出错:', err);
                    }
                });
            } else {
                const noOnlineFriends = document.createElement('div');
                noOnlineFriends.className = 'no-contacts';
                noOnlineFriends.textContent = '没有在线的好友';
                contactsContainer.appendChild(noOnlineFriends);
            }
    
            // 添加所有好友
            const allHeader = document.createElement('div');
            allHeader.className = 'contacts-category';
            allHeader.textContent = `所有好友 (${allFriends.length})`;
            contactsContainer.appendChild(allHeader);
            
            if (allFriends.length > 0) {
                allFriends.forEach(friend => {
                    try {
                        const friendName = friend.username || friend;
                        if (friendName) {
                            // 检查好友是否在线
                            const isOnline = onlineFriends.some(
                                online => (online.username || online) === friendName
                            );
                            addContactToList(friendName, isOnline);
                        } else {
                            console.warn('好友数据无效:', friend);
                        }
                    } catch (err) {
                        console.error('处理所有好友时出错:', err);
                    }
                });
            } else {
                const noFriends = document.createElement('div');
                noFriends.className = 'no-contacts';
                noFriends.textContent = '没有添加任何好友';
                contactsContainer.appendChild(noFriends);
            }
            
            console.log('联系人列表渲染完成');
            
            // 重新绑定点击事件
            try {
                setupContactItemClickHandlers();
            } catch (err) {
                console.error('设置联系人点击处理程序时出错:', err);
            }
            
            // 替换为彩色头像
            try {
                replaceAvatars();
            } catch (err) {
                console.error('替换头像时出错:', err);
            }
        } catch (err) {
            console.error('渲染联系人列表时出错:', err);
        }
    }

    // ... existing code ...

    // 添加联系人到列表的函数修改
    function addContactToList(name, isOnline = false) {
        try {
            const contactsContainer = document.querySelector('.contacts .list');
            if (!contactsContainer) {
                console.error('找不到联系人容器元素 .contacts .list');
                return null;
            }
            
            // 检查名称是否有效
            if (!name) {
                console.error('添加联系人时未提供有效名称');
                return null;
            }
            
            console.log(`添加联系人: ${name}, 在线状态: ${isOnline}`);
            
            // 检查联系人是否已存在，避免重复添加
            const existingContact = document.querySelector(`.contact-item[data-name="${name}"]`);
            if (existingContact) {
                // 更新状态而不是重复添加
                existingContact.className = `contact-item ${isOnline ? 'online' : 'offline'}`;
                const statusIndicator = existingContact.querySelector('.status-indicator');
                if (statusIndicator) {
                    statusIndicator.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
                }
                return existingContact;
            }
            
            const contactItem = document.createElement('div');
            contactItem.className = `contact-item ${isOnline ? 'online' : 'offline'}`;
            contactItem.setAttribute('data-name', name);
            
            try {
                contactItem.innerHTML = `
                    <div class="avatar">${generateAvatar(name)}</div>
                    <div class="name">${name}</div>
                    <div class="status-indicator ${isOnline ? 'online' : 'offline'}"></div>
                `;
            } catch (err) {
                console.error(`为联系人 ${name} 生成HTML时出错:`, err);
                contactItem.innerHTML = `
                    <div class="avatar"><div class="avatar-circle" style="background-color: #ccc;"><span class="avatar-initial">用</span></div></div>
                    <div class="name">${name}</div>
                    <div class="status-indicator ${isOnline ? 'online' : 'offline'}"></div>
                `;
            }
            
            contactsContainer.appendChild(contactItem);
            return contactItem;
        } catch (err) {
            console.error('添加联系人到列表时出错:', err);
            return null;
        }
    }

    // ... existing code ...

    // 强制刷新联系人列表按钮事件
    const refreshContactsButton = document.getElementById('refresh-contacts-button');
    if (refreshContactsButton) {
        refreshContactsButton.addEventListener('click', function() {
            showLoadingOverlay('正在刷新联系人列表...');
            fetchFriendsList()
                .then(() => {
                    hideLoadingOverlay();
                    showSuccessMessage('联系人列表已刷新');
                })
                .catch(error => {
                    hideLoadingOverlay();
                    showErrorMessage(`刷新联系人列表失败: ${error}`);
                });
        });
    }

    // 添加诊断功能按钮
    const diagnosticsButton = document.getElementById('diagnostics-button');
    if (diagnosticsButton) {
        diagnosticsButton.addEventListener('click', function() {
            runConnectionDiagnostics();
        });
    }
    
    // 添加连接状态指示器
    createConnectionStatusIndicator();
    
    // 初始调用一次诊断，确保连接正常
    setTimeout(runConnectionDiagnostics, 3000);
    
    // 设置定期刷新好友列表的计时器
    setInterval(function() {
        if (socket && socket.connected) {
            console.log('定期刷新好友列表...');
            fetchFriendsList()
                .then(() => console.log('定期刷新好友列表成功'))
                .catch(err => console.error('定期刷新好友列表失败:', err));
        }
    }, 30000); // 每30秒刷新一次
    
    // 自动诊断和恢复功能
    function autoRecovery() {
        console.log('运行自动诊断和恢复...');
        
        // 检查联系人列表是否为空，如果为空则尝试重新获取
        if (!Array.isArray(allFriendsList) || allFriendsList.length === 0) {
            console.log('好友列表为空，尝试获取...');
            fetchFriendsList()
                .then(() => console.log('自动恢复好友列表成功'))
                .catch(err => console.error('自动恢复好友列表失败:', err));
        }
        
        // 检查联系人列表元素是否为空，如果为空则尝试重新渲染
        const contactsContainer = document.querySelector('.contacts .list');
        if (contactsContainer && contactsContainer.children.length === 0) {
            console.log('联系人列表容器为空，尝试重新渲染...');
            renderContacts();
        }
        
        // 检查Socket.IO连接
        if (!socket || !socket.connected) {
            console.log('Socket.IO连接断开，尝试重新连接...');
            if (!socket) {
                socket = io();
                console.log('已重新初始化Socket.IO');
            } else {
                socket.connect();
                console.log('已尝试重新连接Socket.IO');
            }
        }
        
        // 检查用户ID是否存在
        if (!currentUserId) {
            console.log('用户ID未设置，尝试获取...');
            fetch('/api/get_current_user')
                .then(response => response.json())
        .then(data => {
            if (data.success) {
                        currentUserId = data.user_id.toString();
                        console.log('自动恢复用户ID成功:', currentUserId);
                        fetchFriendsList();
            } else {
                        console.error('自动恢复用户ID失败:', data.message);
                    }
                })
                .catch(err => console.error('自动恢复用户ID出错:', err));
        }
        
        // 检查generateAvatar函数是否定义
        if (typeof generateAvatar !== 'function') {
            console.error('generateAvatar函数未定义，定义临时替代函数');
            window.generateAvatar = function(name) {
                if (!name) name = "用户";
                return `
                    <div class="avatar-circle" style="background-color: #ccc;">
                        <span class="avatar-initial">${name.charAt(0).toUpperCase()}</span>
                    </div>
                `;
            };
        }
    }
    
    // 页面加载后2秒运行一次自动恢复
    setTimeout(autoRecovery, 2000);
    
    // 之后每分钟运行一次
    setInterval(autoRecovery, 60000);

    // 添加发送消息按钮的事件处理
    const sendButton = document.querySelector('.send-button');
    const messageInput = document.querySelector('.message-input');
    
    if (sendButton && messageInput) {
        console.log('初始化发送消息按钮...');
        
        // 点击发送按钮发送消息
        sendButton.addEventListener('click', function() {
            sendMessage();
        });
        
        // 按下回车键发送消息
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    } else {
        console.error('找不到发送按钮或消息输入框元素');
    }

    // 初始化菜单切换功能
    initMenuSwitcher();
    
    // 初始化侧边栏个人信息
    initUserProfile();

    // 聊天窗口返回按钮
    const backBtn = document.querySelector('.chat-window .back-btn');
    if (backBtn) {
        backBtn.addEventListener('click', function() {
            const chatWindow = document.querySelector('.chat-window');
            const chatList = document.querySelector('.chat-list');
            
            if (chatWindow) {
                chatWindow.classList.remove('active');
            }
            
            if (chatList && window.innerWidth <= 768) {
                chatList.classList.remove('hidden');
            }
        });
    } else {
        console.error('找不到聊天窗口返回按钮');
    }

    // 加载聊天历史记录
    loadChatHistoryFromStorage();
});

// 从localStorage加载聊天历史记录
function loadChatHistoryFromStorage() {
    try {
        console.log('从localStorage加载聊天历史记录...');
        
        // 尝试从localStorage获取历史记录
        const storedHistory = localStorage.getItem('chatHistory');
        if (storedHistory) {
            try {
                // 解析历史记录
                chatHistory = JSON.parse(storedHistory);
                console.log(`加载了 ${Object.keys(chatHistory).length} 个聊天历史记录`);
                
                // 处理历史记录 - 更新聊天列表
                for (const [chatName, messages] of Object.entries(chatHistory)) {
                    if (messages && messages.length > 0) {
                        // 获取最近一条消息
                        const lastMessage = messages[messages.length - 1];
                        // 更新聊天列表显示这条消息
                        updateChatListItem(chatName, lastMessage.content, lastMessage.time);
                    }
                }
            } catch (e) {
                console.error('解析聊天历史记录出错:', e);
                // 重置历史记录
                chatHistory = {};
                localStorage.removeItem('chatHistory');
            }
        } else {
            console.log('没有找到保存的聊天历史记录');
            chatHistory = {};
        }
    } catch (e) {
        console.error('加载聊天历史记录出错:', e);
        chatHistory = {};
    }
}

// ... existing code ...

// 运行连接诊断
function runConnectionDiagnostics() {
    console.log('正在运行连接诊断...');
    showLoadingOverlay('正在进行连接诊断...');
    
    fetch('/api/diagnostics')
        .then(response => response.json())
        .then(data => {
            hideLoadingOverlay();
            if (data.success) {
                console.log('诊断结果:', data);
                let status = [];
                status.push(`用户名: ${data.username}`);
                status.push(`Socket.IO连接: ${data.socketio_connected ? '✓ 已连接' : '✗ 未连接'}`);
                status.push(`Socket.IO ID: ${data.socketio_sid || '未知'}`);
                status.push(`已登录状态: ${data.logged_in ? '✓ 已登录' : '✗ 未登录'}`);
                status.push(`在线好友数: ${data.online_friends.length}`);
                
                showInfoModal('连接诊断结果', status.join('<br>'));
                
                // 如果在线好友数与前端不匹配，自动刷新好友列表
                if (onlineFriendsList.length !== data.online_friends.length) {
                    console.log('在线好友数不匹配，重新获取好友列表');
                    fetchFriendsList();
                }
            } else {
                showErrorMessage(`诊断失败: ${data.message}`);
            }
        })
        .catch(error => {
            hideLoadingOverlay();
            showErrorMessage(`诊断过程出错: ${error}`);
        });
}

// 创建连接状态指示器
function createConnectionStatusIndicator() {
    let indicator = document.getElementById('connection-status');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'connection-status';
        indicator.className = 'connection-status';
        document.body.appendChild(indicator);
        
        indicator.innerHTML = `
            <div class="status-dot disconnected" id="status-dot" title="Socket.IO连接状态"></div>
            <div class="status-tooltip">连接状态: 正在连接...</div>
        `;
        
        // 点击时运行诊断
        indicator.addEventListener('click', function() {
            runConnectionDiagnostics();
        });
    }
    
    // 立即更新连接状态
    updateConnectionStatus();
    return indicator;
}

// 更新连接状态指示器
function updateConnectionStatus() {
    const indicator = document.getElementById('status-dot');
    const tooltip = document.querySelector('.status-tooltip');
    
    if (!indicator || !tooltip) return;
    
    if (!socket) {
        indicator.className = 'status-dot disconnected';
        tooltip.textContent = '连接状态: Socket未初始化';
                    return;
                }
                
    if (socket.connected) {
        indicator.className = 'status-dot connected';
        tooltip.textContent = `连接状态: 已连接 (${socket.id})`;
                    } else {
        indicator.className = 'status-dot disconnected';
        tooltip.textContent = '连接状态: 已断开';
    }
}

    // 替换现有头像为彩色头像
    function replaceAvatars() {
        try {
            console.log("开始替换头像...");
            
            // 替换所有图片元素，添加错误处理
            document.querySelectorAll('img').forEach(img => {
                try {
                    // 跳过已经处理过的图片
                    if (img.hasAttribute('data-avatar-replaced')) {
                    return;
                }
                
                    // 标记为已处理
                    img.setAttribute('data-avatar-replaced', 'true');
                    
                    // 获取用户名（从最近的名称元素或使用默认值）
                    let name = '用户';
                    const parentElement = img.closest('.chat-item, .contact-item, .friend-item, .request-item, .message, .profile-card');
                    if (parentElement) {
                        const nameElement = parentElement.querySelector('.name');
                        if (nameElement) {
                            name = nameElement.textContent.trim();
                        }
                    }
                    
                    // 添加错误处理，替换为彩色头像
                    img.onerror = function() {
                        try {
                            const avatarContainer = this.parentElement;
                            if (avatarContainer && avatarContainer.className.includes('avatar')) {
                                avatarContainer.innerHTML = generateAvatar(name);
                            }
                        } catch (err) {
                            console.error("处理图片错误时出现异常:", err);
                        }
                    };
                    
                    // 触发一次检查，处理已经加载失败的图片
                    if (img.complete && img.naturalHeight === 0) {
                        img.onerror();
                    }
                } catch (err) {
                    console.error("处理单个图片时出现异常:", err);
                }
            });
            
            // 安全替换头像函数
            function safeReplaceAvatar(selector, nameSelector) {
                try {
                    document.querySelectorAll(selector).forEach(avatar => {
                        try {
                            let name = '用户';
                            let nameElement = null;
                            
                            if (typeof nameSelector === 'function') {
                                nameElement = nameSelector(avatar);
                            } else {
                                nameElement = avatar.closest(nameSelector.parent).querySelector(nameSelector.selector);
                            }
                            
                            if (nameElement) {
                                name = nameElement.textContent.trim();
                            }
                            
                            avatar.innerHTML = generateAvatar(name);
                        } catch (err) {
                            console.error(`替换${selector}头像时出现异常:`, err);
                            avatar.innerHTML = generateAvatar('用户');
                        }
                    });
                } catch (err) {
                    console.error(`查询${selector}元素时出现异常:`, err);
                }
            }
            
            // 替换聊天列表中的头像
            safeReplaceAvatar('.chat-item .avatar', {parent: '.chat-item', selector: '.name'});
            
            // 替换联系人列表中的头像
            safeReplaceAvatar('.contact-item .avatar', {parent: '.contact-item', selector: '.name'});
            
            // 替换消息中的头像
            safeReplaceAvatar('.message.received .avatar', function() {
                return document.querySelector('.chat-window .title');
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
            
            console.log("头像替换完成");
        } catch (err) {
            console.error("替换头像过程中出现未捕获异常:", err);
        }
    }

// 设置联系人项点击处理程序
function setupContactItemClickHandlers() {
    try {
        console.log('设置联系人点击事件处理...');
        
        // 移除旧的点击事件监听器
        document.querySelectorAll('.contact-item').forEach(item => {
            // 使用克隆节点替换原节点，移除所有事件监听器
            const newItem = item.cloneNode(true);
            if (item.parentNode) {
                item.parentNode.replaceChild(newItem, item);
            }
        });
        
        // 添加新的点击事件监听器
        document.querySelectorAll('.contact-item').forEach(contactItem => {
            contactItem.addEventListener('click', function() {
                try {
                    const contactName = this.getAttribute('data-name');
                    if (!contactName) {
                        console.warn('联系人项没有data-name属性');
                        return;
                    }
                    
                    console.log(`点击了联系人: ${contactName}`);
                    
                    // 模拟在聊天列表中点击对应的聊天项
                    const chatItem = document.querySelector(`.chat-item[data-name="${contactName}"]`);
                    if (chatItem) {
                        // 如果在聊天列表中已存在该联系人，则模拟点击
                        console.log(`找到现有聊天项: ${contactName}，模拟点击`);
                        chatItem.click();
                    } else {
                        // 如果不存在，则创建新的聊天
                        console.log(`未找到聊天项: ${contactName}，创建新的聊天`);
                        if (typeof setupChat === 'function') {
                            setupChat(contactName);
                        } else {
                            console.error('setupChat函数未定义');
                            // 尝试替代方案
                            createNewChat(contactName);
                        }
                    }
                    
                    // 切换到聊天列表面板
                    const chatListPanel = document.getElementById('chats-panel');
                    const menuItems = document.querySelectorAll('.menu-item');
                    
                    if (chatListPanel && menuItems) {
                        // 隐藏所有面板
                        document.querySelectorAll('.panel').forEach(panel => {
                            panel.classList.remove('active');
                        });
                        
                        // 移除所有菜单项的活动状态
                        menuItems.forEach(item => {
                            item.classList.remove('active');
                        });
                        
                        // 激活聊天面板
                        chatListPanel.classList.add('active');
                        
                        // 激活聊天菜单项
                        if (menuItems.length > 0) {
                            menuItems[0].classList.add('active');
                        }
                    }
                } catch (err) {
                    console.error('处理联系人点击事件时出错:', err);
                }
            });
        });
        
        console.log(`为 ${document.querySelectorAll('.contact-item').length} 个联系人项设置了点击处理程序`);
    } catch (err) {
        console.error('设置联系人点击事件处理程序时出错:', err);
    }
}

// 创建新聊天的替代方法
function createNewChat(contactName) {
    if (!contactName) return;
    
    console.log(`创建新聊天: ${contactName}`);
    
    // 保存当前聊天名称
    currentChat = contactName;
    isCurrentChatGroup = contactName.startsWith('群聊:');
    
    // 在聊天列表中添加新的聊天项
    const chatsList = document.querySelector('.chat-list .list');
    if (chatsList) {
        const chatItem = document.createElement('div');
        chatItem.className = 'chat-item';
        chatItem.setAttribute('data-name', contactName);
        
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const timeStr = `${hours}:${minutes}`;
        
        chatItem.innerHTML = `
            <div class="avatar">${generateAvatar(contactName)}</div>
            <div class="content">
                <div class="name">${contactName}</div>
                <div class="message">开始新的对话</div>
            </div>
            <div class="time">${timeStr}</div>
        `;
        
        chatsList.appendChild(chatItem);
        
        // 为新添加的聊天项添加点击事件
        chatItem.addEventListener('click', function() {
            // 更新聊天窗口标题
            const titleElement = document.querySelector('.chat-window .title');
            if (titleElement) {
                titleElement.textContent = contactName;
            }
            
            // 清空消息区域
            const messagesContainer = document.querySelector('.chat-window .messages');
            if (messagesContainer) {
                messagesContainer.innerHTML = '';
                
                // 添加日期分隔符
                const dateDiv = document.createElement('div');
                dateDiv.className = 'date';
                dateDiv.textContent = '今天';
                messagesContainer.appendChild(dateDiv);
            }
            
            // 显示聊天窗口
            document.querySelector('.chat-window').classList.add('active');
            
            // 在移动设备上隐藏聊天列表
            if (window.innerWidth <= 768) {
                document.querySelector('.chat-list').classList.add('hidden');
            }
        });
        
        // 模拟点击新创建的聊天项
        chatItem.click();
    }
}

// 设置聊天函数
function setupChat(chatName) {
    if (!chatName) return;
    
    console.log(`设置聊天: ${chatName}`);
    
    // 保存当前聊天名称
    currentChat = chatName;
    
    // 判断是否为群聊
    isCurrentChatGroup = chatName.startsWith('群聊:');
    
    // 添加到聊天列表中（如果不存在）
    let chatItem = document.querySelector(`.chat-item[data-name="${chatName}"]`);
    if (!chatItem) {
        // 创建新的聊天项
        const chatsList = document.querySelector('.chat-list .list');
        if (chatsList) {
            console.log(`为 ${chatName} 创建新的聊天项`);
            chatItem = document.createElement('div');
            chatItem.className = 'chat-item';
            chatItem.setAttribute('data-name', chatName);
            
            chatItem.innerHTML = `
                <div class="avatar">${generateAvatar(chatName)}</div>
                        <div class="content">
                    <div class="name">${chatName}</div>
                    <div class="message">开始新的对话</div>
                        </div>
                <div class="time">${getCurrentTime()}</div>
            `;
            
            // 将新项添加到聊天列表顶部
            if (chatsList.firstChild) {
                chatsList.insertBefore(chatItem, chatsList.firstChild);
            } else {
                chatsList.appendChild(chatItem);
            }
            
            // 为新添加的聊天项绑定点击事件
            chatItem.addEventListener('click', function() {
                // 更新聊天窗口内容
                updateChatWindowContent(chatName);
                
                // 更新窗口可见性
                document.querySelector('.chat-window').classList.add('active');
                
                // 在移动设备上隐藏聊天列表
                if (window.innerWidth <= 768) {
                    document.querySelector('.chat-list').classList.add('hidden');
                }
            });
        } else {
            console.error('找不到聊天列表容器');
            return null;
        }
    }
    
    // 模拟点击聊天项，打开聊天窗口
    if (chatItem) {
        console.log(`点击聊天项 ${chatName} 打开聊天窗口`);
        chatItem.click();
    }
    
    return chatItem;
}

// 获取当前时间（格式化为HH:MM）
    function getCurrentTime() {
        const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
}

// 更新聊天窗口内容
function updateChatWindowContent(chatName) {
    if (!chatName) return;
    
    console.log(`更新聊天窗口内容: ${chatName}`);
    
    // 更新当前聊天状态
    currentChat = chatName;
    isCurrentChatGroup = chatName.startsWith('群聊:');
    
    // 更新窗口标题
    const titleElement = document.querySelector('.chat-window .title');
    if (titleElement) {
        titleElement.textContent = chatName;
    }
    
    // 显示/隐藏群组成员按钮
    const groupMembersBtn = document.getElementById('group-members-btn');
    const dissolveGroupBtn = document.getElementById('dissolve-group-btn');
    if (groupMembersBtn) {
        groupMembersBtn.style.display = isCurrentChatGroup ? 'block' : 'none';
    }
    if (dissolveGroupBtn) {
        dissolveGroupBtn.style.display = isCurrentChatGroup ? 'block' : 'none';
    }
    
    // 清空并加载聊天记录
    const messagesContainer = document.querySelector('.chat-window .messages');
    if (messagesContainer) {
        // 清空现有消息
        messagesContainer.innerHTML = '';
        
        // 添加日期分隔符
        const dateDiv = document.createElement('div');
        dateDiv.className = 'date';
        dateDiv.textContent = new Date().toLocaleDateString();
        messagesContainer.appendChild(dateDiv);
        
        // 加载历史消息
        loadChatHistory(chatName, messagesContainer);
    }
    
    // 滚动到底部
    scrollToBottom();
}

// 加载聊天历史记录
function loadChatHistory(chatName, container) {
    if (!chatName || !container) return;
    
    // 从全局变量或localStorage中获取聊天历史
    const history = chatHistory[chatName] || [];
    console.log(`加载聊天历史: ${chatName}, 消息数: ${history.length}`);
    
    if (history.length === 0) {
        // 没有聊天历史，显示提示
        const emptyMessage = document.createElement('div');
        emptyMessage.className = 'empty-chat';
        emptyMessage.textContent = '没有聊天记录，开始新的对话吧！';
        container.appendChild(emptyMessage);
        return;
    }
            
    // 添加消息到容器
    history.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${msg.isSent ? 'sent' : 'received'}`;
        
        // 构建消息HTML - 根据消息类型决定显示样式
        if (msg.isSent) {
            // 发送的消息 - 显示在右侧，不显示头像
            messageDiv.innerHTML = `
                <div class="content">
                    <div class="bubble">${msg.content}</div>
                    <div class="time">${msg.time}</div>
                </div>
            `;
        } else {
            // 接收的消息 - 显示在左侧，显示头像
            messageDiv.innerHTML = `
                <div class="avatar">${generateAvatar(chatName)}</div>
                <div class="content">
                    <div class="bubble">${msg.content}</div>
                    <div class="time">${msg.time}</div>
                </div>
            `;
        }
        
        container.appendChild(messageDiv);
    });
    
    // 滚动到底部
    scrollToBottom();
}

// 滚动聊天窗口到底部
function scrollToBottom() {
    const messagesContainer = document.querySelector('.chat-window .messages');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// 更新聊天列表中好友状态
function updateChatListFriendStatus() {
    try {
        console.log('更新聊天列表好友状态...');
        
        // 确保onlineFriendsList是数组
        if (!Array.isArray(onlineFriendsList)) {
            console.warn('onlineFriendsList 不是数组，使用空数组');
            onlineFriendsList = [];
        }
        
        const chatItems = document.querySelectorAll('.chat-item');
        console.log(`找到 ${chatItems.length} 个聊天项目`);
        
        chatItems.forEach(item => {
            try {
                const friendName = item.getAttribute('data-name');
                if (!friendName) {
                    console.warn('聊天项目没有data-name属性');
                    return;
                }
                
                if (friendName.startsWith('群聊:')) {
                    console.log(`跳过群聊: ${friendName}`);
                    return;
                }
                
                // 检查好友是否在线
                const isOnline = onlineFriendsList.some(
                    friend => (friend && (friend.username || friend) === friendName)
                );
                
                console.log(`更新好友 ${friendName} 状态: ${isOnline ? '在线' : '离线'}`);
                
                // 更新状态指示器
                const statusIndicator = item.querySelector('.status-indicator');
                if (statusIndicator) {
                    statusIndicator.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
                }
                
                // 更新名称元素，添加状态指示器
                const nameElement = item.querySelector('.name');
                if (nameElement) {
                    // 移除现有状态指示器
                    const existingIndicator = nameElement.querySelector('.status-indicator');
                    if (existingIndicator) {
                        existingIndicator.remove();
                    }
                    
                    // 添加新的状态指示器
                    const indicator = document.createElement('span');
                    indicator.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
                    nameElement.appendChild(indicator);
                }
            } catch (err) {
                console.error('更新单个聊天项目状态时出错:', err);
            }
        });
        
        console.log('聊天列表好友状态更新完成');
    } catch (err) {
        console.error('更新聊天列表好友状态时出错:', err);
    }
}

// 更新好友状态
function updateFriendStatus(friendName, isOnline) {
    if (!friendName) return;
    
    console.log(`更新好友状态: ${friendName} - ${isOnline ? '在线' : '离线'}`);
    
    // 更新联系人列表中的状态
    const contactItem = document.querySelector(`.contact-item[data-name="${friendName}"]`);
    if (contactItem) {
        contactItem.classList.toggle('online', isOnline);
        contactItem.classList.toggle('offline', !isOnline);
        
        const statusIndicator = contactItem.querySelector('.status-indicator');
        if (statusIndicator) {
            statusIndicator.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
        }
    }
    
    // 更新聊天列表中的状态
    const chatItem = document.querySelector(`.chat-item[data-name="${friendName}"]`);
    if (chatItem) {
        const nameElement = chatItem.querySelector('.name');
        if (nameElement) {
            // 移除现有状态指示器
            const existingIndicator = nameElement.querySelector('.status-indicator');
            if (existingIndicator) {
                existingIndicator.remove();
            }
            
            // 添加新的状态指示器
            const indicator = document.createElement('span');
            indicator.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
            nameElement.appendChild(indicator);
        }
    }
    
    // 如果是当前聊天对象，更新窗口标题中的状态
    if (currentChat === friendName) {
        const titleElement = document.querySelector('.chat-window .title');
        if (titleElement) {
            // 更新标题文本，添加状态信息
            titleElement.textContent = `${friendName} ${isOnline ? '(在线)' : '(离线)'}`;
        }
    }
}

// 接收消息处理函数
function receiveMessage(data, isSentByMe = false) {
    console.log('执行receiveMessage函数，接收到的数据:', data, '是否为自己发送:', isSentByMe);
    
    if (!data || !data.sender || !data.content) {
        console.error('接收到无效消息格式:', data);
        return;
    }
    
    // 确保所有ID都转为字符串进行比较
    const sender = data.sender.toString();
    const recipient = data.recipient ? data.recipient.toString() : '';
    const content = data.content;
    const time = data.time || getCurrentTime();
    
    console.log('处理消息，发送者:', sender, '接收者:', recipient, '当前用户:', currentUserId.toString());
    
    // 重新判断一次是否是自己发送的消息
    isSentByMe = (sender === currentUserId.toString());
    
    // 确定消息的聊天对象
    // 如果是自己发送的消息，聊天对象是接收者(recipient)
    // 如果是他人发送的消息，聊天对象是发送者(sender)
    const chatTarget = isSentByMe ? recipient : sender;
    
    console.log(`${isSentByMe ? '发送' : '接收'}消息 ${isSentByMe ? '到' : '来自'} ${chatTarget}:`, content);
    console.log(`当前聊天对象: ${currentChat}, 是否为当前聊天: ${currentChat === chatTarget}`);
            
    // 确保聊天对象的聊天历史记录存在
    if (!chatHistory[chatTarget]) {
        console.log(`为 ${chatTarget} 创建新的聊天历史记录`);
        chatHistory[chatTarget] = [];
    }
    
    // 添加消息到历史记录
    chatHistory[chatTarget].push({
        content: content,
        time: time,
        isSent: isSentByMe // 根据是否为自己发送设置标记
    });
    console.log(`消息已添加到历史记录，当前历史记录长度: ${chatHistory[chatTarget].length}`);
    
    // 保存聊天历史到localStorage
    try {
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
        console.log('聊天历史已保存到localStorage');
    } catch (e) {
        console.error('保存聊天历史到localStorage失败:', e);
    }
    
    // 确保聊天项存在于聊天列表中
    let chatItem = document.querySelector(`.chat-item[data-name="${chatTarget}"]`);
    if (!chatItem) {
        console.log(`聊天列表中不存在 ${chatTarget} 的聊天项，创建新的`);
        chatItem = setupChat(chatTarget);
    }
    
    // 如果当前正在与聊天对象聊天，则显示消息
    if (currentChat === chatTarget) {
        console.log('当前正在与聊天对象聊天，直接显示消息');
        const messagesContainer = document.querySelector('.chat-window .messages');
        if (messagesContainer) {
            console.log('找到消息容器元素');
            const messageDiv = document.createElement('div');
            
            // 根据消息是否为自己发送来设置样式
            messageDiv.className = isSentByMe ? 'message sent' : 'message received';
            
                         // 构建消息的HTML结构
             // 检查消息类型
             const isImage = content.startsWith('data:image/') || data.type === 'image';
             
             if (isSentByMe) {
                 // 发送方显示在右侧，不显示头像
                 if (isImage) {
                     messageDiv.innerHTML = `
                         <div class="content">
                             <div class="bubble"><img src="${content}" alt="发送的图片" /></div>
                             <div class="time">${time}</div>
                         </div>
                     `;
                 } else {
                     messageDiv.innerHTML = `
                         <div class="content">
                             <div class="bubble">${content}</div>
                             <div class="time">${time}</div>
                         </div>
                     `;
                 }
             } else {
                 // 接收方显示在左侧，显示头像
                 if (isImage) {
                     messageDiv.innerHTML = `
                         <div class="avatar">${generateAvatar(sender)}</div>
                         <div class="content">
                             <div class="bubble"><img src="${content}" alt="接收的图片" /></div>
                             <div class="time">${time}</div>
                         </div>
                     `;
                 } else {
                     messageDiv.innerHTML = `
                         <div class="avatar">${generateAvatar(sender)}</div>
                         <div class="content">
                             <div class="bubble">${content}</div>
                             <div class="time">${time}</div>
                         </div>
                     `;
                 }
             }
            
            console.log('创建的消息HTML:', messageDiv.outerHTML);
            messagesContainer.appendChild(messageDiv);
            console.log('消息已添加到消息容器');
            
            // 滚动到底部
            scrollToBottom();
        } else {
            console.error('找不到消息容器元素 .chat-window .messages');
        }
    } else {
        console.log(`当前聊天对象与消息目标不同，不直接显示消息`);
    }
    
    // 更新聊天列表项
    console.log(`更新聊天列表项: ${chatTarget}`);
    updateChatListItem(chatTarget, content, time);
    
    // 如果是接收到的消息且不在当前聊天窗口，则显示通知
    if (!isSentByMe && currentChat !== chatTarget) {
        console.log(`显示系统通知`);
        showNotification(sender, content);
    }
    
    console.log('receiveMessage函数执行完毕');
}

// 显示系统通知
function showNotification(title, message) {
    // 检查通知权限
    if (Notification.permission === "granted") {
        new Notification(title, {
            body: message,
            icon: '../static/img/chat.svg'
        });
    } else if (Notification.permission !== "denied") {
                    Notification.requestPermission().then(permission => {
                        if (permission === "granted") {
                new Notification(title, {
                    body: message,
                    icon: '../static/img/chat.svg'
                            });
                        }
                    });
    }
}

// 显示成功消息
function showSuccessMessage(message) {
    showToast(message, 'success');
}

// 显示错误消息
function showErrorMessage(message) {
    showToast(message, 'error');
}

// 显示信息消息
function showInfoMessage(message) {
    showToast(message, 'info');
}

// 显示Toast消息
function showToast(message, type = 'info') {
    // 创建Toast容器（如果不存在）
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    // 创建Toast元素
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    // 添加到容器
    toastContainer.appendChild(toast);
    
    // 淡入效果
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // 3秒后删除
    setTimeout(() => {
        toast.classList.remove('show');
        
        setTimeout(() => {
            toastContainer.removeChild(toast);
        }, 300);
    }, 3000);
}

// 显示加载遮罩
function showLoadingOverlay(message = '加载中...') {
    let overlay = document.getElementById('loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-message">${message}</div>
        `;
        document.body.appendChild(overlay);
    } else {
        overlay.querySelector('.loading-message').textContent = message;
        overlay.style.display = 'flex';
    }
}

// 隐藏加载遮罩
function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

// 显示信息模态框
function showInfoModal(title, content) {
    // 检查是否已有模态框
    let infoModal = document.getElementById('info-modal');
    if (!infoModal) {
        // 创建模态框
        infoModal = document.createElement('div');
        infoModal.id = 'info-modal';
        infoModal.className = 'modal';
        
        infoModal.innerHTML = `
            <div class="modal-content">
                <span class="close-btn">&times;</span>
                <h2 class="modal-title"></h2>
                <div class="modal-body"></div>
                <div class="modal-footer">
                    <button class="primary-btn">确定</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(infoModal);
        
        // 关闭按钮事件
        const closeBtn = infoModal.querySelector('.close-btn');
        const confirmBtn = infoModal.querySelector('.primary-btn');
        
        closeBtn.addEventListener('click', () => {
            infoModal.style.display = 'none';
        });
        
        confirmBtn.addEventListener('click', () => {
            infoModal.style.display = 'none';
        });
        
        // 点击外部关闭
        window.addEventListener('click', (e) => {
            if (e.target === infoModal) {
                infoModal.style.display = 'none';
            }
        });
    }
    
    // 更新内容
    const titleElement = infoModal.querySelector('.modal-title');
    const bodyElement = infoModal.querySelector('.modal-body');
    
    titleElement.textContent = title;
    bodyElement.innerHTML = content;
    
    // 显示模态框
    infoModal.style.display = 'flex';
}

    // 更新聊天列表项
    function updateChatListItem(name, message, time) {
        try {
            if (!name) {
                console.error('updateChatListItem: 无效的名称');
                return;
            }
            
            console.log(`更新聊天列表项: ${name}, 消息: ${message}, 时间: ${time}`);
            
            // 检查聊天列表中是否已存在
            let chatItem = null;
            try {
                chatItem = document.querySelector(`.chat-item[data-name="${name}"]`);
            } catch (err) {
                console.error(`查询聊天项目 ${name} 时出错:`, err);
            }
            
            const chatsList = document.querySelector('.chat-list .list');
            
            if (!chatsList) {
                console.error('找不到聊天列表容器元素');
                return;
            }
            
            // 如果不存在，创建新的
            if (!chatItem) {
                console.log(`为 ${name} 创建新的聊天列表项`);
                chatItem = document.createElement('div');
                chatItem.className = 'chat-item';
                
                // 确保名称有效并设置data-name属性
                if (typeof name === 'string' && name.trim() !== '') {
                    chatItem.setAttribute('data-name', name);
                } else {
                    console.error(`无效的聊天名称: ${name}，使用默认名称`);
                    chatItem.setAttribute('data-name', '聊天');
                }
                
                // 生成聊天项的HTML内容
                try {
                    const avatarContent = typeof generateAvatar === 'function' ? 
                        generateAvatar(name) : 
                        `<div class="avatar-circle" style="background-color: #ccc;"><span class="avatar-initial">${(name || '用户').charAt(0).toUpperCase()}</span></div>`;
                    
                    chatItem.innerHTML = `
                        <div class="avatar">${avatarContent}</div>
                        <div class="content">
                            <div class="name">${name || '聊天'}</div>
                            <div class="message">${message || '开始新的对话'}</div>
                        </div>
                        <div class="time">${time || getCurrentTime()}</div>
                    `;
                } catch (err) {
                    console.error(`生成聊天项HTML时出错:`, err);
                    chatItem.innerHTML = `
                        <div class="avatar"><div class="avatar-circle" style="background-color: #ccc;"><span class="avatar-initial">用</span></div></div>
                        <div class="content">
                            <div class="name">${name || '聊天'}</div>
                            <div class="message">开始新的对话</div>
                        </div>
                        <div class="time">${getCurrentTime()}</div>
                    `;
                }
                
                // 添加点击事件
                chatItem.addEventListener('click', function() {
                    try {
                        const chatName = this.getAttribute('data-name');
                        console.log(`点击了聊天项: ${chatName}`);
                        
                        if (typeof updateChatWindowContent === 'function') {
                            updateChatWindowContent(chatName);
                        } else {
                            console.error('updateChatWindowContent函数未定义');
                            // 简单更新聊天窗口
                            const titleElement = document.querySelector('.chat-window .title');
                            if (titleElement) {
                                titleElement.textContent = chatName;
                            }
                            
                            // 清空消息区域
                            const messagesContainer = document.querySelector('.chat-window .messages');
                            if (messagesContainer) {
                                messagesContainer.innerHTML = `<div class="date">今天</div>`;
                            }
                        }
                        
                        // 显示聊天窗口
                        const chatWindow = document.querySelector('.chat-window');
                        if (chatWindow) {
                            chatWindow.classList.add('active');
                        }
                        
                        // 在移动设备上隐藏聊天列表
                        if (window.innerWidth <= 768) {
                            const chatList = document.querySelector('.chat-list');
                            if (chatList) {
                                chatList.classList.add('hidden');
                            }
                        }
                    } catch (err) {
                        console.error('处理聊天项点击事件时出错:', err);
                    }
                });
                
                // 添加到列表顶部
                try {
                    if (chatsList.firstChild) {
                        chatsList.insertBefore(chatItem, chatsList.firstChild);
                    } else {
                        chatsList.appendChild(chatItem);
                    }
                } catch (err) {
                    console.error(`添加聊天项到列表时出错:`, err);
                    chatsList.appendChild(chatItem);
                }
            } 
            // 如果存在，则更新并移到顶部
            else {
                try {
                    // 如果已经是第一个，则不需要移动
                    if (chatItem !== chatsList.firstChild) {
                        chatsList.removeChild(chatItem);
                        chatsList.insertBefore(chatItem, chatsList.firstChild);
                    }
                } catch (err) {
                    console.error(`移动现有聊天项时出错:`, err);
                }
            }
            
            // 更新内容
            if (message) {
                try {
                    const messageElement = chatItem.querySelector('.message');
                    if (messageElement) {
                        messageElement.textContent = message;
                    }
                } catch (err) {
                    console.error(`更新消息内容时出错:`, err);
                }
            }
            
            // 更新时间
            if (time) {
                try {
                    const timeElement = chatItem.querySelector('.time');
                    if (timeElement) {
                        timeElement.textContent = time;
                    }
                } catch (err) {
                    console.error(`更新时间时出错:`, err);
                }
            }
            
            // 更新在线状态
            try {
                if (Array.isArray(onlineFriendsList)) {
                    const isOnline = onlineFriendsList.some(
                        friend => friend && (friend.username || friend) === name
                    );
                    
                    const nameElement = chatItem.querySelector('.name');
                    if (nameElement) {
                        // 移除现有状态指示器
                        const existingIndicator = nameElement.querySelector('.status-indicator');
                        if (existingIndicator) {
                            existingIndicator.remove();
                        }
                        
                        // 添加新的状态指示器
                        const indicator = document.createElement('span');
                        indicator.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
                        nameElement.appendChild(indicator);
                    }
                }
            } catch (err) {
                console.error(`更新好友状态时出错:`, err);
            }
            
            // 替换头像
            try {
                const avatarElement = chatItem.querySelector('.avatar');
                if (avatarElement) {
                    if (typeof generateAvatar === 'function') {
                        avatarElement.innerHTML = generateAvatar(name);
                    } else {
                        avatarElement.innerHTML = `<div class="avatar-circle" style="background-color: #ccc;"><span class="avatar-initial">${(name || '用户').charAt(0).toUpperCase()}</span></div>`;
                    }
                }
            } catch (err) {
                console.error(`替换头像时出错:`, err);
            }
        } catch (err) {
            console.error(`updateChatListItem函数执行出错:`, err);
        }
    }

// 显示好友请求通知
function showFriendRequestNotification(data) {
    if (!data || !data.username) {
        console.error('无效的好友请求数据:', data);
        return;
    }
    
    const username = data.username;
    const message = `${username} 想添加您为好友`;
    
    // 显示系统通知
    showNotification('新的好友请求', message);
    
    // 显示界面通知
    showInfoModal('新的好友请求', `
        <div class="friend-request-notification">
            <div class="avatar">${generateAvatar(username)}</div>
            <div class="request-details">
                <div class="name">${username}</div>
                    <div class="message">${message}</div>
                </div>
            <div class="actions">
                <button class="primary-btn accept-btn" data-username="${username}">接受</button>
                <button class="secondary-btn reject-btn" data-username="${username}">拒绝</button>
            </div>
        </div>
    `);
    
    // 绑定接受和拒绝按钮事件
    const acceptBtn = document.querySelector(`.accept-btn[data-username="${username}"]`);
    const rejectBtn = document.querySelector(`.reject-btn[data-username="${username}"]`);
    
    if (acceptBtn) {
        acceptBtn.addEventListener('click', function() {
            acceptFriendRequest(username);
            document.getElementById('info-modal').style.display = 'none';
        });
    }
    
    if (rejectBtn) {
        rejectBtn.addEventListener('click', function() {
            rejectFriendRequest(username);
            document.getElementById('info-modal').style.display = 'none';
        });
    }
    
    // 自动更新好友管理界面
    updateFriendManagementUI();
}

// 接受好友请求
function acceptFriendRequest(username) {
    if (!username) return;
    
    showLoadingOverlay('正在接受好友请求...');
    
    fetch('/api/add_friend', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ friend_username: username }),
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        hideLoadingOverlay();
        
        if (data.success) {
            showSuccessMessage(`已接受 ${username} 的好友请求`);
            fetchFriendsList(); // 刷新好友列表
        } else {
            showErrorMessage(`接受好友请求失败: ${data.message}`);
        }
    })
    .catch(error => {
        hideLoadingOverlay();
        showErrorMessage(`接受好友请求出错: ${error}`);
    });
}

// 拒绝好友请求
function rejectFriendRequest(username) {
    if (!username) return;
    
    showSuccessMessage(`已拒绝 ${username} 的好友请求`);
    
    // 这里可以添加拒绝好友请求的API调用
    // ...
}

// 发送消息函数
function sendMessage(type = 'text', content = null) {
    try {
        console.log('准备发送消息...');
        
        // 如果没有当前聊天，则不发送
        if (!currentChat) {
            showErrorMessage('请先选择一个聊天对象');
            return;
        }
        
        // 获取消息内容
        const messageInput = document.querySelector('.message-input');
        if (!messageInput) {
            console.error('找不到消息输入框');
            return;
        }
        
        // 如果没有提供内容且输入框为空，则不发送
        if (!content) {
            content = messageInput.value.trim();
        }
        
        if (!content) {
            return;
        }
        
        console.log(`发送${type}消息到 ${currentChat}: ${content}`);
        
        // 当前时间
        const time = getCurrentTime();
        
        // 将消息显示和保存的逻辑移至receiveMessage函数，这样可以统一处理
        // 构造一个消息数据对象
        const messageData = {
            sender: currentUserId, // 发送者是当前用户
            recipient: currentChat, // 接收者是当前聊天对象
            content: content,
            time: time
        };
        
        
        // 通过Socket.IO发送消息
        if (socket && socket.connected) {
            socket.emit('send_message', {
                sender: currentUserId,
                recipient: currentChat,
                message: content,
                type: type
            });
        } else {
            console.error('Socket.IO未连接，无法发送消息');
            showErrorMessage('连接已断开，消息将在重新连接后发送');
        }
        
        // 清空输入框
        messageInput.value = '';
        
        // 聚焦回输入框
        messageInput.focus();
    } catch (err) {
        console.error('发送消息时出错:', err);
        showErrorMessage('发送消息失败');
    }
}

// 显示添加好友模态框
function showAddFriendModal() {
    try {
        console.log('显示添加好友模态框');
        
        // 移除可能存在的旧模态框（避免重复创建导致的问题）
        const existingModal = document.getElementById('add-friend-modal');
        if (existingModal) {
            document.body.removeChild(existingModal);
        }
        
        // 创建新的模态框
        const modal = document.createElement('div');
        modal.id = 'add-friend-modal';
        modal.className = 'modal';
        
        // 添加用户搜索功能 - 优化UI设计，移除底部添加按钮
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2 class="modal-title">添加好友</h2>
                    <span class="close-btn">&times;</span>
                </div>
                <div class="modal-body">
                    <p class="search-desc">请输入用户名进行搜索</p>
                    <div class="search-container">
                        <input type="text" id="friend-username" placeholder="输入用户名搜索" autocomplete="off">
                        <button id="search-user-btn">搜索</button>
                    </div>
                    <div id="search-results" class="search-results">
                        <!-- 搜索结果将显示在这里 -->
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // 获取模态框中的元素
        const closeBtn = modal.querySelector('.close-btn');
        const usernameInput = modal.querySelector('#friend-username');
        const searchBtn = modal.querySelector('#search-user-btn');
        const searchResults = modal.querySelector('#search-results');
        
        // 搜索按钮事件
        if (searchBtn) {
            searchBtn.addEventListener('click', function() {
                const searchTerm = usernameInput.value.trim();
                if (searchTerm) {
                    searchUser(searchTerm, searchResults);
                } else {
                    showErrorMessage('请输入用户名进行搜索');
                }
            });
        }
        
        // 输入框回车事件
        if (usernameInput) {
            usernameInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const searchTerm = usernameInput.value.trim();
                    if (searchTerm) {
                        searchUser(searchTerm, searchResults);
                    } else {
                        showErrorMessage('请输入用户名进行搜索');
                    }
                }
            });
        }
        
        // 使用通用关闭模态框函数
        const closeThisModal = function() {
            closeModal('add-friend-modal');
        };
        
        // 关闭按钮事件
        if (closeBtn) {
            closeBtn.addEventListener('click', closeThisModal);
        }
        
        // 点击模态框外部关闭
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeThisModal();
            }
        });
        
        // 显示模态框
        modal.style.display = 'flex';
        
        // 添加动画效果
        setTimeout(() => {
            modal.classList.add('show');
            const modalContent = modal.querySelector('.modal-content');
            if (modalContent) {
                modalContent.style.opacity = '1';
                modalContent.style.transform = 'scale(1)';
            }
        }, 10);
        
        // 聚焦到输入框
        setTimeout(() => {
            if (usernameInput) {
                usernameInput.focus();
            }
        }, 100);
    } catch (err) {
        console.error('显示添加好友模态框时出错:', err);
        // 确保加载遮罩被隐藏
        hideLoadingOverlay();
    }
}

// 事件处理函数，避免匿名函数重复绑定
function searchInputHandler(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        const searchInput = document.querySelector('#search-friend-input');
        const searchResults = document.querySelector('#add-friend-modal .search-result');
        if (searchInput && searchResults) {
            const searchTerm = searchInput.value.trim();
            if (searchTerm) {
                searchUser(searchTerm, searchResults);
            } else {
                showErrorMessage('请输入用户名进行搜索');
            }
        }
    }
}

function searchBtnHandler() {
    const searchInput = document.querySelector('#search-friend-input');
    const searchResults = document.querySelector('#add-friend-modal .search-result');
    if (searchInput && searchResults) {
        const searchTerm = searchInput.value.trim();
        if (searchTerm) {
            searchUser(searchTerm, searchResults);
        } else {
            showErrorMessage('请输入用户名进行搜索');
        }
    }
}

function closeBtnHandler(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    const modal = document.getElementById('add-friend-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 显示搜索加载动画
function showSearchLoading(container) {
    if (!container) return;
    
    container.innerHTML = `
        <div class="search-loading">
            <div class="loading-spinner"></div>
            <p>正在搜索用户...</p>
        </div>
    `;
}

// 用户搜索函数
function searchUser(username, resultsContainer) {
    if (!username || !resultsContainer) {
        console.error('搜索用户参数不完整');
        return;
    }

    console.log(`正在搜索用户: ${username}`);
    // 显示搜索中动画
    showSearchLoading(resultsContainer);
    
    // 发送用户搜索请求
    fetch('/api/search_user', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: username
        }),
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 404) {
                // API可能未实现，使用模拟数据
                console.log('API未实现，使用模拟数据');
                return {
                    success: true,
                    users: [
                        {
                            username: username,
                            user_id: 'mock_' + Math.random().toString(36).substr(2, 9)
                        }
                    ]
                };
            }
            throw new Error(`HTTP错误! 状态: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('搜索结果:', data);
        
        // 清空结果容器
        resultsContainer.innerHTML = '';
        
        if (data.success && data.users && data.users.length > 0) {
            // 显示搜索结果
            data.users.forEach(user => {
                const userItem = document.createElement('div');
                userItem.className = 'user-item';
                userItem.setAttribute('data-username', user.username);
                
                // 生成头像
                const avatarContent = typeof generateAvatar === 'function' ? 
                    generateAvatar(user.username) : 
                    `<div class="avatar-circle" style="background-color: #ccc;"><span class="avatar-initial">${user.username.charAt(0).toUpperCase()}</span></div>`;
                
                userItem.innerHTML = `
                    <div class="avatar">
                        ${avatarContent}
                    </div>
                    <div class="user-info">
                        <div class="name">${user.username}</div>
                        <div class="id">ID: ${user.user_id || '未知'}</div>
                    </div>
                    <button class="add-btn">添加</button>
                `;
                
                // 添加点击事件
                userItem.addEventListener('click', function() {
                    // 移除其他选中状态
                    document.querySelectorAll('.user-item').forEach(item => {
                        item.classList.remove('selected');
                    });
                    // 设置当前选中
                    this.classList.add('selected');
                });
                
                // 添加按钮点击事件
                const addBtn = userItem.querySelector('.add-btn');
                if (addBtn) {
                    addBtn.addEventListener('click', function(e) {
                        e.stopPropagation(); // 防止触发整个item的点击事件
                        addFriend(user.username);
                        closeModal('add-friend-modal');
                    });
                }
                
                resultsContainer.appendChild(userItem);
            });
        } else {
            // 无搜索结果
            resultsContainer.innerHTML = `
                <div class="no-results">
                    <div class="emoji">😕</div>
                    <p>未找到匹配的用户 "${username}"</p>
                    <p>请尝试使用其他关键词搜索</p>
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('搜索用户出错:', error);
        resultsContainer.innerHTML = `
            <div class="error-message">
                <div class="emoji">😓</div>
                <p>搜索过程中出错</p>
                <p>${error.message || '请稍后重试'}</p>
            </div>
        `;
    });
}

// 原模拟搜索结果函数已移除，现使用真实API

// 添加好友函数
function addFriend(username) {
    if (!username) {
        showErrorMessage('请输入好友用户名');
        return;
    }
    
    console.log(`正在添加好友: ${username}`);
    showLoadingOverlay('正在添加好友...');
    
    // 发送添加好友请求
    fetch('/api/add_friend', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            friend_username: username
        }),
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP错误，状态: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        hideLoadingOverlay();
        
        if (data.success) {
            showSuccessMessage(`成功添加好友: ${username}`);
            // 刷新好友列表
            fetchFriendsList();
            
            // 关闭可能打开的模态框
            closeModal('add-friend-modal');
        } else {
            showErrorMessage(`添加好友失败: ${data.message || '未知错误'}`);
        }
    })
    .catch(error => {
        hideLoadingOverlay();
        console.error('添加好友请求出错:', error);
        showErrorMessage('添加好友请求出错，请稍后再试');
        
        // 尝试处理API不可用的情况（模拟成功添加）
        if (error.message.includes('404')) {
            console.log('API可能未实现，模拟添加好友成功');
            showSuccessMessage(`模拟添加好友成功: ${username}`);
            
            // 模拟刷新好友列表
            setTimeout(() => {
                fetchFriendsList();
                
                // 关闭模态框
                closeModal('add-friend-modal');
            }, 1000);
        }
    });
}

// 删除好友函数
function removeFriend(username) {
    if (!username) {
        showErrorMessage('未指定要删除的好友');
        return;
    }
    
    if (!confirm(`确定要删除好友 ${username} 吗？`)) {
        return;
    }
    
    console.log(`正在删除好友: ${username}`);
    showLoadingOverlay('正在删除好友...');
    
    // 发送删除好友请求
    fetch('/api/remove_friend', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            friend_username: username
        }),
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        hideLoadingOverlay();
        
        if (data.success) {
            showSuccessMessage(`成功删除好友: ${username}`);
            // 刷新好友列表
            fetchFriendsList();
            
            // 如果当前聊天对象是被删除的好友，则关闭聊天窗口
            if (currentChat === username) {
                document.querySelector('.chat-window').classList.remove('active');
                currentChat = null;
            }
            
            // 从聊天列表中移除
            const chatItem = document.querySelector(`.chat-item[data-name="${username}"]`);
            if (chatItem && chatItem.parentNode) {
                chatItem.parentNode.removeChild(chatItem);
            }
        } else {
            showErrorMessage(`删除好友失败: ${data.message}`);
        }
    })
    .catch(error => {
        hideLoadingOverlay();
        console.error('删除好友请求出错:', error);
        showErrorMessage('删除好友请求出错，请稍后再试');
    });
}

// 初始化菜单切换功能
function initMenuSwitcher() {
    try {
        console.log('初始化菜单切换功能...');
        
        const menuItems = document.querySelectorAll('.menu-item');
        if (!menuItems || menuItems.length === 0) {
            console.error('找不到菜单项元素');
            return;
        }
        
        // 获取所有面板
        const panels = {
            'chats': document.getElementById('chats-panel'),
            'contacts': document.getElementById('contacts-panel'),
            'profile': document.getElementById('profile-panel')
        };
        
        // 为每个菜单项添加点击事件
        menuItems.forEach(item => {
            item.addEventListener('click', function() {
                try {
                    const panelId = this.getAttribute('data-panel');
                    if (!panelId) {
                        console.warn('菜单项没有data-panel属性');
                        return;
                    }
                    
                    console.log(`切换到面板: ${panelId}`);
                    
                    // 移除所有菜单项的活动状态
                    menuItems.forEach(mi => mi.classList.remove('active'));
                    
                    // 设置当前菜单项为活动状态
                    this.classList.add('active');
                    
                    // 隐藏所有面板
                    Object.values(panels).forEach(panel => {
                        if (panel) {
                            panel.classList.remove('active');
                        }
                    });
                    
                    // 显示选中的面板
                    const panel = panels[panelId];
                    if (panel) {
                        panel.classList.add('active');
                    } else {
                        console.error(`找不到面板: ${panelId}`);
                    }
                    
                    // 如果切换到联系人面板，刷新联系人列表
                    if (panelId === 'contacts') {
                        fetchFriendsList();
                    }
                } catch (err) {
                    console.error('处理菜单项点击事件时出错:', err);
                }
            });
        });
        
        console.log('菜单切换功能初始化完成');
    } catch (err) {
        console.error('初始化菜单切换功能时出错:', err);
    }
}

// 初始化用户个人资料
function initUserProfile() {
    try {
        console.log('初始化用户个人资料...');
        
        // 获取当前用户信息
        fetch('/api/get_current_user')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 更新侧边栏头像和个人资料页面
                    const username = data.username || '当前用户';
                    const userId = data.user_id;
                    
                    // 更新用户ID
                    currentUserId = userId;
                    
                    console.log(`获取到用户信息: ${username} (ID: ${userId})`);
                    
                    // 更新侧边栏头像
                    const sidebarAvatar = document.querySelector('.sidebar .avatar');
                    if (sidebarAvatar) {
                        sidebarAvatar.innerHTML = generateAvatar(username);
                    }
                    
                    // 更新个人资料页面
                    const profileCard = document.querySelector('.profile-card');
                    if (profileCard) {
                        const nameElement = profileCard.querySelector('.name');
                        const idElement = profileCard.querySelector('.id');
                        const avatarElement = profileCard.querySelector('.avatar');
                        
                        if (nameElement) nameElement.textContent = username;
                        if (idElement) idElement.textContent = `账号: ${userId}`;
                        if (avatarElement) avatarElement.innerHTML = generateAvatar(username);
                    }
                    
                    // 初始化退出登录按钮
                    const logoutBtn = document.getElementById('logout-btn');
                    if (logoutBtn) {
                        logoutBtn.addEventListener('click', function() {
                            logout();
                        });
                    }
                } else {
                    console.error('获取用户信息失败:', data.message);
                }
            })
            .catch(error => {
                console.error('获取用户信息请求出错:', error);
            });
        
    } catch (err) {
        console.error('初始化用户个人资料时出错:', err);
    }
}

// 退出登录函数
function logout() {
    if (confirm('确定要退出登录吗？')) {
        console.log('正在退出登录...');
        showLoadingOverlay('正在退出登录...');
        
        fetch('/api/logout', {
            method: 'POST',
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            hideLoadingOverlay();
            
            if (data.success) {
                showSuccessMessage('已成功退出登录');
                // 重定向到登录页面
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1000);
            } else {
                showErrorMessage(`退出登录失败: ${data.message}`);
            }
        })
        .catch(error => {
            hideLoadingOverlay();
            console.error('退出登录请求出错:', error);
            showErrorMessage('退出登录请求出错，请稍后再试');
        });
    }
}

// 添加好友按钮的事件处理函数
function addFriendBtnHandler(event) {
    console.log('添加好友按钮被点击');
    event.preventDefault();
    event.stopPropagation();
    showAddFriendModal();
}

// 确保在页面切换或刷新时清理所有模态框和遮罩
window.addEventListener('beforeunload', function() {
    // 隐藏加载遮罩
    hideLoadingOverlay();
    
    // 关闭所有可能打开的模态框
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (modal.parentNode) {
            modal.parentNode.removeChild(modal);
        }
    });
});

// 在网络错误时自动恢复UI状态
window.addEventListener('online', function() {
    console.log('网络连接已恢复');
    // 隐藏可能显示的加载遮罩
    hideLoadingOverlay();
    // 刷新数据
    fetchFriendsList();
});

window.addEventListener('offline', function() {
    console.log('网络连接已断开');
    showErrorMessage('网络连接已断开，部分功能可能不可用');
});

// 添加全局错误处理，确保UI不会卡住
window.addEventListener('error', function(event) {
    console.error('全局错误:', event.error);
    // 隐藏可能显示的加载遮罩
    hideLoadingOverlay();
    // 关闭可能打开的模态框
    const modals = document.querySelectorAll('.modal');
    if (modals.length > 0) {
        modals.forEach(modal => {
            modal.style.display = 'none';
        });
    }
});

// 在页面加载完成后确保添加好友按钮绑定
document.addEventListener('DOMContentLoaded', function() {
    // 添加好友按钮点击事件
    const addFriendBtn = document.getElementById('add-friend-btn');
    if (addFriendBtn) {
        addFriendBtn.addEventListener('click', addFriendBtnHandler);
    }
    
    // 诊断按钮点击事件
    const diagnosticsBtn = document.getElementById('diagnostics-button');
    if (diagnosticsBtn) {
        diagnosticsBtn.addEventListener('click', runConnectionDiagnostics);
    }
});

// 保存上次诊断结果
let lastDiagnostics = null;
let instanceRecoveryAttempts = 0;
const MAX_RECOVERY_ATTEMPTS = 3;

// 添加页面加载处理，调用API恢复实例
document.addEventListener('DOMContentLoaded', function() {
    // 等待DOM加载完成后执行
    console.log("页面加载完成，尝试恢复实例...");
    
    // 调用页面加载API以恢复实例
    fetch('/api/page_loaded', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        console.log("页面加载API响应:", data);
        
        if (data.success) {
            console.log(`实例已恢复 - 用户名: ${data.username}, 实例ID: ${data.instance_id}`);
            
            // 存储诊断数据
            lastDiagnostics = data;
            instanceRecoveryAttempts = 0;
            
            // 启动定期检查
            startPeriodicChecks();
        } else {
            console.error("实例恢复失败:", data.message);
            
            // 如果API返回重定向指令，则执行重定向
            if (data.action === 'redirect' && data.redirect_url) {
                console.log(`重定向到: ${data.redirect_url}`);
                window.location.href = data.redirect_url;
            } else {
                // 否则尝试重新获取诊断信息
                checkInstanceHealth();
            }
        }
    })
    .catch(error => {
        console.error("调用页面加载API出错:", error);
        // 出错时尝试诊断
        setTimeout(checkInstanceHealth, 1000);
    });
});

// 启动定期检查
function startPeriodicChecks() {
    // 1. 定期心跳
    setInterval(sendHeartbeat, 20000); // 每20秒发送一次心跳
    
    // 2. 定期实例健康检查
    setInterval(checkInstanceHealth, 30000); // 每30秒检查一次
    
    // 3. 立即发送一次心跳
    sendHeartbeat();
    
    // 4. 立即进行一次健康检查
    setTimeout(checkInstanceHealth, 5000);
    
    console.log("定期检查已启动");
}

// 发送心跳函数
function sendHeartbeat() {
    console.log("发送心跳...");
    fetch('/api/heartbeat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log("心跳发送成功，实例注册表已更新");
        } else {
            console.error("心跳发送失败:", data.message);
            // 心跳失败可能表示会话已失效，尝试恢复
            checkInstanceHealth();
        }
    })
    .catch(error => {
        console.error("发送心跳时出错:", error);
    });
}

// 检查实例健康状态函数
function checkInstanceHealth() {
    console.log("检查实例健康状态...");
    fetch('/api/diagnostics', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        // 保存诊断结果
        lastDiagnostics = data;
        
        if (!data.success) {
            console.error("实例健康检查失败:", data.message);
            
            // 如果有恢复建议，记录下来
            if (data.recovery) {
                console.log("恢复建议:", data.recovery);
            }
            
            // 如果有其他实例，考虑切换
            if (data.other_instances && data.other_instances.length > 0) {
                console.log("发现其他实例:", data.other_instances);
                
                // 尝试切换到其他实例
                if (instanceRecoveryAttempts < MAX_RECOVERY_ATTEMPTS) {
                    instanceRecoveryAttempts++;
                    const targetInstance = data.other_instances[0].instance_id;
                    console.log(`尝试切换到实例 ${targetInstance}，第 ${instanceRecoveryAttempts} 次尝试`);
                    
                    // 通过SocketIO强制重连
                    if (window.socket) {
                        window.socket.emit('force_reconnect', { instance_id: targetInstance });
                    }
                    
                    // 刷新页面
                    setTimeout(() => {
                        location.reload();
                    }, 2000);
                } else {
                    console.error("已达到最大恢复尝试次数，需要重新登录");
                    showInstanceLostWarning();
                }
            } else if (instanceRecoveryAttempts < MAX_RECOVERY_ATTEMPTS) {
                // 没有其他实例但仍在尝试次数内，重新加载页面尝试恢复
                instanceRecoveryAttempts++;
                console.log(`尝试通过重新加载页面恢复，第 ${instanceRecoveryAttempts} 次尝试`);
                
                // 刷新页面
                setTimeout(() => {
                    location.reload();
                }, 2000);
            } else {
                // 已达到最大尝试次数，显示警告
                console.error("已达到最大恢复尝试次数，需要重新登录");
                showInstanceLostWarning();
            }
        } else {
            console.log("实例健康检查通过:", data.instance_id);
            // 检查通过，重置恢复尝试计数
            instanceRecoveryAttempts = 0;
            
            // 检查是否有需要更新的UI元素
            updateStatusUI(data);
        }
    })
    .catch(error => {
        console.error("调用诊断API出错:", error);
        
        // 增加恢复尝试计数
        instanceRecoveryAttempts++;
        
        if (instanceRecoveryAttempts >= MAX_RECOVERY_ATTEMPTS) {
            showInstanceLostWarning();
        }
    });
}

// 显示实例丢失警告
function showInstanceLostWarning() {
    // 检查是否已经显示过警告
    if (document.getElementById('instance-lost-warning')) {
        return;
    }
    
    // 创建警告元素
    const warningDiv = document.createElement('div');
    warningDiv.id = 'instance-lost-warning';
    warningDiv.className = 'instance-lost-warning';
    warningDiv.innerHTML = `
        <div class="warning-content">
            <h3>连接诊断失败</h3>
            <p>您的客户端实例似乎已丢失。请尝试重新登录。</p>
            <button onclick="location.href='/logout'">重新登录</button>
        </div>
    `;
    
    // 添加样式
    const style = document.createElement('style');
    style.textContent = `
        .instance-lost-warning {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0, 0, 0, 0.7);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .warning-content {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            max-width: 400px;
            text-align: center;
        }
        .warning-content button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 15px;
        }
    `;
    
    // 添加到页面
    document.head.appendChild(style);
    document.body.appendChild(warningDiv);
}

// 更新状态UI
function updateStatusUI(data) {
    // 更新状态图标
    const statusIcon = document.getElementById('connection-status-icon');
    if (statusIcon) {
        if (data.socketio_connected) {
            statusIcon.className = 'status-icon connected';
            statusIcon.title = '已连接';
        } else {
            statusIcon.className = 'status-icon disconnected';
            statusIcon.title = '连接断开';
        }
    }
    
    // 更新在线好友列表
    if (data.online_friends && window.updateOnlineFriendsList) {
        window.updateOnlineFriendsList(data.online_friends);
    }
}

// 添加页面卸载事件处理，确保实例正确清理
window.addEventListener('beforeunload', function() {
    // 页面卸载前发送一次心跳，更新最后活跃时间
    navigator.sendBeacon('/api/heartbeat', JSON.stringify({}));
    
    // 注意：不能在这里调用异步函数，因为页面将很快卸载
    console.log("页面即将卸载，已发送最后心跳");
});

// 添加自动心跳和断线重连功能
let heartbeatInterval = null;
let reconnectInterval = null;
let lastHeartbeatResponse = Date.now();
let instanceId = null; // 存储当前实例ID

// 启动心跳
function startHeartbeat() {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
    }
    
    heartbeatInterval = setInterval(() => {
        // 发送心跳请求
        $.ajax({
            url: '/api/heartbeat',
            method: 'POST',
            success: function(response) {
                // 更新最后心跳响应时间
                lastHeartbeatResponse = Date.now();
                
                // 存储实例ID
                if (response && response.instance_id) {
                    instanceId = response.instance_id;
                }
                
                // 检查连接状态
                checkConnectionStatus();
            },
            error: function(xhr, status, error) {
                console.log('心跳请求失败:', error);
                checkConnectionStatus();
            }
        });
    }, 10000); // 每10秒发送一次心跳
}

// 检查连接状态
function checkConnectionStatus() {
    const now = Date.now();
    const timeSinceLastHeartbeat = now - lastHeartbeatResponse;
    
    // 如果超过30秒没有收到心跳响应，尝试重连
    if (timeSinceLastHeartbeat > 30000) {
        console.log('检测到连接可能断开，尝试重连...');
        attemptReconnect();
    }
}

// 尝试重连
function attemptReconnect() {
    // 获取诊断信息
    $.ajax({
        url: '/api/diagnostics',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                console.log('诊断成功，连接正常');
                lastHeartbeatResponse = Date.now();
            } else {
                console.log('诊断显示连接异常，检查活跃实例...');
                
                // 如果有其他活跃实例，尝试切换
                if (response.active_instances && response.active_instances.length > 0) {
                    const availableInstances = response.active_instances.filter(inst => inst.instance_id !== instanceId);
                    
                    if (availableInstances.length > 0) {
                        console.log('找到其他活跃实例，尝试切换...');
                        forceReconnect(availableInstances[0].instance_id);
                    } else {
                        console.log('没有找到其他活跃实例，尝试重新加载页面');
                        location.reload();
                    }
                } else {
                    console.log('没有可用的实例，尝试重新加载页面');
                    location.reload();
                }
            }
        },
        error: function(xhr, status, error) {
            console.log('诊断请求失败，重新加载页面', error);
            location.reload();
        }
    });
}

// 强制重连到指定实例
function forceReconnect(targetInstanceId) {
    if (socket) {
        // 使用SocketIO的强制重连功能
        socket.emit('force_reconnect', {
            instance_id: targetInstanceId
        });
        
        // 更新实例ID
        instanceId = targetInstanceId;
        lastHeartbeatResponse = Date.now();
        console.log('已切换到实例:', targetInstanceId);
    } else {
        console.log('SocketIO未初始化，重新加载页面');
        location.reload();
    }
}

// 页面加载完成后执行
$(document).ready(function() {
    // 初始化页面
    console.log('页面加载完成，初始化中...');
    
    // 通知服务器页面已加载
    $.ajax({
        url: '/api/page_loaded',
        method: 'POST',
        success: function(response) {
            console.log('页面加载通知成功', response);
            
            // 存储实例ID
            if (response && response.instance_id) {
                instanceId = response.instance_id;
            }
            
            // 启动心跳
            startHeartbeat();
        },
        error: function(xhr, status, error) {
            console.log('页面加载通知失败:', error);
        }
    });
    
    // 初始化其他功能
    initializeChatFunctions();
    refreshFriendsList();
    
    // 设置自动刷新好友列表的间隔
    setInterval(refreshFriendsList, 30000); // 每30秒刷新一次好友列表
});

// 初始化聊天功能
function initializeChatFunctions() {
    // 连接SocketIO
    socket = io();
    
    // 注册SocketIO事件监听器
    registerSocketEvents(socket);
    
    // 添加发送消息的事件处理
    $('#send-message-form').on('submit', function(e) {
        e.preventDefault();
        sendMessage();
    });
    
    // 添加好友的事件处理
    $('#add-friend-form').on('submit', function(e) {
        e.preventDefault();
        addFriend();
    });
    
    // 处理聊天窗口切换
    $('.friend-list').on('click', '.friend-item', function() {
        const friendUsername = $(this).data('username');
        switchChatTo(friendUsername);
    });
    
    // 初始化emoji选择器
    initializeEmojiPicker();
}

// 注册SocketIO事件监听器
function registerSocketEvents(socket) {
    // 处理连接事件
    socket.on('connect', function() {
        console.log('SocketIO连接成功');
        lastHeartbeatResponse = Date.now();
    });
    
    // 处理断开连接事件
    socket.on('disconnect', function() {
        console.log('SocketIO连接断开');
        // 断开连接后不要立即重连，让心跳机制来处理
    });
    
    // 处理重连结果事件
    socket.on('reconnect_result', function(data) {
        console.log('重连结果:', data);
        if (data.success) {
            console.log('重连成功，实例ID:', data.instance_id);
            instanceId = data.instance_id;
            lastHeartbeatResponse = Date.now();
        } else {
            console.log('重连失败，将重新加载页面');
            location.reload();
        }
    });
    
    // 处理接收消息事件
    socket.on('receive_message', function(data) {
        displayMessage(data.sender, data.message);
    });
    
    // 处理消息状态更新事件
    socket.on('message_status', function(data) {
        updateMessageStatus(data.status, data.message);
    });
    
    // 处理好友添加事件
    socket.on('friend_added', function(data) {
        displayNotification(`${data.friend} ${data.message}`);
        refreshFriendsList();
    });
    
    // 处理在线好友更新事件
    socket.on('online_friends_updated', function(data) {
        updateOnlineFriends(data.online_friends);
    });
    
    // 处理好友列表刷新事件
    socket.on('friends_refreshed', function(data) {
        updateFriendsList(data.online_friends, data.all_friends);
    });
    
    // 处理注册表更新事件
    socket.on('registry_update', function(data) {
        console.log('实例注册表更新:', data);
    });
}

// 在页面关闭前发送通知
$(window).on('beforeunload', function() {
    // 停止心跳
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
    }
    
    // 通知服务器页面关闭
    navigator.sendBeacon('/api/heartbeat', JSON.stringify({
        action: 'page_closing',
        instance_id: instanceId
    }));
});

// 其他原有功能...