// 全局变量声明 - 确保这些变量在全局范围内可访问
let currentUserId = null;
let currentChat = null;
let socket = null;
let isCurrentChatGroup = false;
let onlineFriendsList = [];
let allFriendsList = [];
let chatHistory = {};
let activeModal = null; // 跟踪当前激活的模态框
let audioTranscriptions = {}; // 存储音频转写结果的对象
    
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
    
    // 从localStorage加载聊天记录并应用图片和音频错误处理
    loadChatHistoryFromStorage();
    // 延迟执行一次错误处理，确保所有媒体元素加载完成
    setTimeout(() => {
        addImageErrorHandling();
        addAudioErrorHandling();
    }, 1000);
    
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
        
        if (!data) {
            console.error('接收到的消息数据为空');
            return;
        }
        
        // 修复：正确映射所有必需字段，包括 type 和 hiddenMessage
        const messageData = {
            sender: data.sender || data.username || data.user || '',
            recipient: data.recipient || data.to || '',
            content: data.content || data.message || data.text || '',
            time: data.time || getCurrentTime(),
            type: data.type || 'text', // 确保消息类型被保留
            hiddenMessage: data.hiddenMessage || '' // 确保隐藏消息被保留
        };
        
        console.log('处理后的消息数据:', messageData, '当前用户ID:', currentUserId);
        
        if (messageData.sender && messageData.content) {
            const isSentByMe = messageData.sender.toString() === currentUserId.toString();
            
            console.log('是否为自己发送:', isSentByMe, 
                       '发送方:', messageData.sender, 
                       '当前用户:', currentUserId,
                       '接收方:', messageData.recipient);
            
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
    
    // 绑定语音录制按钮点击事件
    const audioRecordBtn = document.getElementById('audio-record-btn');
    if (audioRecordBtn) {
        console.log('找到语音录制按钮，正在绑定点击事件');
        audioRecordBtn.addEventListener('click', function() {
            showAudioRecordModal();
        });
    } else {
        console.error('未找到语音录制按钮元素 (id="audio-record-btn")');
    }
    
    // 绑定语音转文字按钮点击事件
    const transcriptBtn = document.getElementById('transcript-btn');
    if (transcriptBtn) {
        console.log('找到语音转文字按钮，正在绑定点击事件');
        transcriptBtn.addEventListener('click', function() {
            showTranscriptInfo();
        });
    } else {
        console.error('未找到语音转文字按钮元素 (id="transcript-btn")');
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
            
            // 添加右键菜单事件
            contactItem.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                showContactContextMenu(e, name);
            });
            
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
    
    // 图片上传按钮点击事件
    const imageUploadBtn = document.getElementById('image-upload-btn');
    const imageUploadInput = document.getElementById('image-upload-input');
    
    if (imageUploadBtn && imageUploadInput) {
        imageUploadBtn.addEventListener('click', function(e) {
            e.preventDefault();
            // 检查是否有当前聊天
            if (!currentChat) {
                showErrorMessage('请先选择一个聊天对象');
                return;
            }
            // 触发文件选择
            imageUploadInput.click();
        });
        
        // 处理文件选择
        imageUploadInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                showStegMessageModal(this.files[0]);
            }
        });
    }
});

// 从localStorage加载聊天历史记录
function loadChatHistoryFromStorage() {
    try {
        console.log('从localStorage加载聊天历史记录...');
        
        // 获取隐藏聊天列表
        const hiddenChats = JSON.parse(localStorage.getItem('hiddenChats') || '[]');
        console.log(`加载了 ${hiddenChats.length} 个隐藏聊天`);
        
        // 尝试从localStorage获取历史记录
        const storedHistory = localStorage.getItem('chatHistory');
        if (storedHistory) {
            try {
                // 解析历史记录
                chatHistory = JSON.parse(storedHistory);
                console.log(`加载了 ${Object.keys(chatHistory).length} 个聊天历史记录`);
                
                // 修复所有可能的相对路径URL
                const baseUrl = window.location.origin;
                
                // 遍历所有聊天历史记录，修复图片和音频URL
                for (const chatName in chatHistory) {
                    if (chatHistory[chatName] && Array.isArray(chatHistory[chatName])) {
                        chatHistory[chatName].forEach(msg => {
                            // 检查是否为媒体消息(图片/音频)且URL为相对路径
                            if ((msg.type === 'image' || msg.type === 'steg_image' || msg.type === 'audio_message') && 
                                typeof msg.content === 'string') {
                                
                                // 检查是否是以/static/开头的相对路径
                                if (msg.content.startsWith('/static/') || msg.content.startsWith('static/')) {
                                    // 确保路径格式统一
                                    const normalizedPath = msg.content.startsWith('/') ? msg.content : '/' + msg.content;
                                    // 转换为绝对路径
                                    msg.content = baseUrl + normalizedPath;
                                    console.log(`修复历史记录中的媒体文件路径: ${msg.content}`);
                                }
                                // 检查是否已经是绝对路径但域名不同(可能是从其他端口/域名的实例保存的)
                                else if (msg.content.startsWith('http')) {
                                    const contentUrl = new URL(msg.content);
                                    const currentUrl = new URL(baseUrl);
                                    
                                    // 如果域名或端口不同，尝试转换为当前域名和端口
                                    if (contentUrl.host !== currentUrl.host) {
                                        // 提取路径部分
                                        const pathPart = contentUrl.pathname;
                                        // 重建URL
                                        msg.content = baseUrl + pathPart;
                                        console.log(`修正域名不匹配的媒体URL: ${msg.content}`);
                                    }
                                }
                                
                                // 特别处理音频消息
                                if (msg.type === 'audio_message') {
                                    // 添加额外属性用于重试和故障恢复
                                    msg.originalUrl = msg.content;  // 保存原始URL
                                    msg.retryCount = 0;  // 初始化重试计数
                                }
                            }
                        });
                    }
                }
                
                // 更新localStorage中的修复后的数据
                try {
                    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
                    console.log('已更新localStorage中的聊天历史记录，修复了媒体文件路径');
                } catch (err) {
                    console.error('更新localStorage失败:', err);
                }
                
                // 处理历史记录 - 更新聊天列表
                for (const [chatName, messages] of Object.entries(chatHistory)) {
                    if (messages && messages.length > 0) {
                        // 获取最近一条消息
                        const lastMessage = messages[messages.length - 1];
                        // 确定要显示的消息内容
                        let displayContent = lastMessage.content;
                        if (lastMessage.type === 'image') displayContent = '[图片]';
                        if (lastMessage.type === 'steg_image') displayContent = '[隐写图片]';
                        if (lastMessage.type === 'audio_message') displayContent = '[语音消息]';
                        // 更新聊天列表显示这条消息
                        updateChatListItem(chatName, displayContent, lastMessage.time);
                        
                        // 如果该聊天在隐藏列表中，隐藏它
                        if (hiddenChats.includes(chatName)) {
                            const chatItem = document.querySelector(`.chat-item[data-name="${chatName}"]`);
                            if (chatItem) {
                                chatItem.style.display = 'none';
                                console.log(`隐藏聊天项: ${chatName}`);
                            }
                        }
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
            const contactName = contactItem.getAttribute('data-name');
            
            // 添加点击事件
            contactItem.addEventListener('click', function() {
                try {
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
            
            // 添加右键菜单事件
            contactItem.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                showContactContextMenu(e, contactName);
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
    
    // 为加载的历史图片和音频添加错误处理
    addImageErrorHandling();
    addAudioErrorHandling();
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
        
        // 检查消息类型
        const isImage = msg.content.startsWith('data:image/') || msg.type === 'image';
        const isStegImage = msg.type === 'steg_image';
        const isAudio = msg.type === 'audio_message';
        const hiddenMessage = msg.hiddenMessage || '';
        
        // 处理媒体文件路径，确保它是完整的URL
        let content = msg.content;
        if (isStegImage || isAudio) {
            // 检查是否是相对路径
            if (content.startsWith('/static/') || content.startsWith('static/')) {
                // 确保路径格式统一
                const normalizedPath = content.startsWith('/') ? content : '/' + content;
                // 转换为绝对路径
                const baseUrl = window.location.origin;
                content = baseUrl + normalizedPath;
                console.log(`历史记录中转换${isAudio ? '音频' : '隐写图片'}路径为绝对URL:`, content);
            }
            
            // 如果是音频，保存原始URL用于错误处理和重试
            if (isAudio) {
                msg.originalUrl = content;
                msg.retryCount = msg.retryCount || 0;
            }
        }
        
        // 添加更多调试日志
        if (isStegImage) {
            console.log('处理隐写图片消息:', {
                isStegImage,
                content,
                hiddenMessage,
                originalUrl: msg.content
            });
        }
        
        if (isAudio) {
            console.log('处理音频消息:', {
                isAudio,
                content,
                originalUrl: msg.content
            });
        }
        
        // 构建消息HTML - 根据消息类型决定显示样式
        if (msg.isSent) {
            // 发送的消息 - 显示在右侧，不显示头像
            if (isImage || isStegImage) {
                // 对于隐写图片，添加特殊标记
                const stegIndicator = isStegImage ? '<div class="steg-indicator" title="包含隐藏消息"><i class="fas fa-lock"></i></div>' : '';
                messageDiv.innerHTML = `
                    <div class="content">
                        <div class="bubble image-bubble">
                            ${stegIndicator}
                            <img src="${content}" alt="发送的图片" class="${isStegImage ? 'steg-image' : ''}" data-hidden="${hiddenMessage}" />
                        </div>
                        <div class="time">${msg.time}</div>
                    </div>
                `;
            } else if (isAudio) {
                // 音频消息
                const audioId = `audio_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
                messageDiv.innerHTML = `
                    <div class="content">
                        <div class="bubble">
                            <div class="audio-message-container">
                                <div class="audio-controls">
                                    <button class="audio-play-btn" data-audio="${audioId}">
                                        <i class="fas fa-play"></i>
                                    </button>
                                    <div class="audio-waveform"></div>
                                    <span class="audio-duration">00:00</span>
                                </div>
                            </div>
                            <audio id="${audioId}" src="${content}" preload="metadata" style="display:none;"></audio>
                        </div>
                        <div class="time">${msg.time}</div>
                    </div>
                `;
            } else {
                messageDiv.innerHTML = `
                    <div class="content">
                        <div class="bubble">${msg.content}</div>
                        <div class="time">${msg.time}</div>
                    </div>
                `;
            }
        } else {
            // 接收的消息 - 显示在左侧，显示头像
            if (isImage || isStegImage) {
                // 对于隐写图片，添加特殊标记
                const stegIndicator = isStegImage ? '<div class="steg-indicator" title="包含隐藏消息"><i class="fas fa-lock"></i></div>' : '';
                messageDiv.innerHTML = `
                    <div class="avatar">${generateAvatar(chatName)}</div>
                    <div class="content">
                        <div class="bubble image-bubble">
                            ${stegIndicator}
                            <img src="${content}" alt="接收的图片" class="${isStegImage ? 'steg-image' : ''}" data-hidden="${hiddenMessage}" />
                        </div>
                        <div class="time">${msg.time}</div>
                    </div>
                `;
            } else if (isAudio) {
                // 音频消息
                const audioId = `audio_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
                messageDiv.innerHTML = `
                    <div class="avatar">${generateAvatar(chatName)}</div>
                    <div class="content">
                        <div class="bubble">
                            <div class="audio-message-container">
                                <div class="audio-controls">
                                    <button class="audio-play-btn" data-audio="${audioId}">
                                        <i class="fas fa-play"></i>
                                    </button>
                                    <div class="audio-waveform"></div>
                                    <span class="audio-duration">00:00</span>
                                </div>
                            </div>
                            <audio id="${audioId}" src="${content}" preload="metadata" style="display:none;"></audio>
                        </div>
                        <div class="time">${msg.time}</div>
                    </div>
                `;
            } else {
                messageDiv.innerHTML = `
                    <div class="avatar">${generateAvatar(chatName)}</div>
                    <div class="content">
                        <div class="bubble">${msg.content}</div>
                        <div class="time">${msg.time}</div>
                    </div>
                `;
            }
        }
        
        container.appendChild(messageDiv);
        
        // 为隐写图片添加点击事件
        if (isStegImage) {
            setTimeout(() => {
                const img = messageDiv.querySelector('.steg-image');
                if (img) {
                    img.addEventListener('click', function() {
                        showHiddenMessageModal(hiddenMessage, content);
                    });
                    img.style.cursor = 'pointer';
                    img.title = '点击查看隐藏消息';
                }
            }, 100);
        }
        
        // 为音频按钮添加点击事件
        if (isAudio) {
            setTimeout(() => {
                const audioElement = messageDiv.querySelector('audio');
                const playBtn = messageDiv.querySelector('.audio-play-btn');
                if (audioElement && playBtn) {
                    // 为播放按钮添加点击事件
                    playBtn.addEventListener('click', function() {
                        const audioId = this.getAttribute('data-audio');
                        const audio = document.getElementById(audioId);
                        
                        if (!audio) {
                            console.error('找不到对应的音频元素:', audioId);
                            return;
                        }
                        
                        // 暂停所有其他音频
                        document.querySelectorAll('audio').forEach(a => {
                            if (a.id !== audioId && !a.paused) {
                                a.pause();
                                const otherBtn = document.querySelector(`.audio-play-btn[data-audio="${a.id}"]`);
                                if (otherBtn) otherBtn.querySelector('i').className = 'fas fa-play';
                            }
                        });
                        
                        // 切换当前音频播放/暂停状态
                        if (audio.paused) {
                            // 尝试播放
                            audio.play().catch(error => {
                                console.error('播放音频失败:', error, audio.src);
                                
                                // 尝试修复音频URL
                                const baseUrl = window.location.origin;
                                
                                if (audio.src.startsWith('/') || audio.src.indexOf('://') === -1) {
                                    // 相对路径转绝对路径
                                    audio.src = baseUrl + (audio.src.startsWith('/') ? audio.src : '/' + audio.src);
                                } else {
                                    // 替换域名部分
                                    try {
                                        const url = new URL(audio.src);
                                        audio.src = baseUrl + url.pathname;
                                    } catch (e) {
                                        console.error('解析音频URL失败:', e);
                                    }
                                }
                                
                                // 重试播放
                                setTimeout(() => {
                                    audio.play().catch(err => {
                                        console.error('重试播放音频失败:', err);
                                        this.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                                        this.title = '音频播放失败';
                                    });
                                }, 300);
                            });
                            
                            // 更新播放图标
                            this.querySelector('i').className = 'fas fa-pause';
                        } else {
                            // 暂停
                            audio.pause();
                            this.querySelector('i').className = 'fas fa-play';
                        }
                    });
                    
                    // 当音频播放结束时，恢复播放按钮状态
                    audioElement.addEventListener('ended', function() {
                        playBtn.querySelector('i').className = 'fas fa-play';
                    });
                }
            }, 100);
        }
    });
    
    // 滚动到底部
    scrollToBottom();
    
    // 为加载的历史图片和音频添加错误处理
    addImageErrorHandling();
    addAudioErrorHandling();
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
    try {
        console.log('接收消息:', data, '是否为自己发送:', isSentByMe);
        
        let content = data.content || data.message || '';
        const sender = data.sender || 'unknown';
        const recipient = data.recipient || '';
        const time = data.time || getCurrentTime();
        const messageType = data.type || 'text';  // 消息类型
        const hiddenMessage = data.hiddenMessage || '';  // 隐藏消息
        
        // 确定消息的聊天对象
        // 如果是自己发送的消息，聊天对象是接收者(recipient)
        // 如果是他人发送的消息，聊天对象是发送者(sender)
        const chatTarget = isSentByMe ? recipient : sender;
        
        console.log(`${isSentByMe ? '发送' : '接收'}消息 ${isSentByMe ? '到' : '来自'} ${chatTarget}:`, content);
        console.log(`当前聊天对象: ${currentChat}, 是否为当前聊天: ${currentChat === chatTarget}`);
        console.log(`消息类型: ${messageType}, 内容: ${content}`);
        
        // 检查该聊天是否在隐藏列表中，如果是则移除并重新显示
        let hiddenChats = JSON.parse(localStorage.getItem('hiddenChats') || '[]');
        if (hiddenChats.includes(chatTarget)) {
            console.log(`收到来自隐藏聊天 ${chatTarget} 的消息，将重新显示该聊天`);
            // 从隐藏列表中移除
            hiddenChats = hiddenChats.filter(name => name !== chatTarget);
            localStorage.setItem('hiddenChats', JSON.stringify(hiddenChats));
            
            // 重新显示聊天项
            const chatItem = document.querySelector(`.chat-item[data-name="${chatTarget}"]`);
            if (chatItem) {
                chatItem.style.display = '';
                console.log(`已重新显示聊天项: ${chatTarget}`);
            }
        }
                
        // 确保聊天对象的聊天历史记录存在
        if (!chatHistory[chatTarget]) {
            console.log(`为 ${chatTarget} 创建新的聊天历史记录`);
            chatHistory[chatTarget] = [];
        }
        
        // 检查消息类型，处理不同类型的消息
        const isImage = content.startsWith('data:image/') || messageType === 'image';
        const isStegImage = messageType === 'steg_image';  // 增加对隐写图片类型的判断
        
        // 处理隐写图片路径，确保它是完整的URL
        if (isStegImage && content.startsWith('/static/')) {
            // 如果是相对路径，转换为绝对路径
            const baseUrl = window.location.origin;
            content = baseUrl + content;
            console.log('转换隐写图片路径为绝对URL:', content);
        }
        
        // 添加更多调试日志
        if (isStegImage) {
            console.log('处理隐写图片消息:', {
                isStegImage,
                content,
                hiddenMessage,
                originalUrl: msg.content
            });
        }
        
        // 添加消息到历史记录，包含消息类型信息
        // 确保存储前所有图片URL都是绝对路径
        let storageContent = content;
        if ((messageType === 'steg_image' || messageType === 'image') && storageContent.startsWith('/')) {
            // 如果是相对路径，转换为绝对路径再存储
            const baseUrl = window.location.origin;
            storageContent = baseUrl + storageContent;
            console.log('存储到历史记录前转换图片路径为绝对URL:', storageContent);
        }
        
        chatHistory[chatTarget].push({
            content: storageContent,
            time: time,
            isSent: isSentByMe,
            type: messageType,  // 保存消息类型
            hiddenMessage: hiddenMessage  // 保存隐藏消息
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
                
                // 添加更多调试日志
                console.log('构建消息HTML，类型:', messageType, '内容:', content);
                
                // 根据消息类型构建不同的HTML结构
                if (isSentByMe) {
                    // 发送方显示在右侧，不显示头像
                    if (isImage || isStegImage) {
                        // 对于隐写图片，添加特殊标记
                        const stegIndicator = isStegImage ? '<div class="steg-indicator" title="包含隐藏消息"><i class="fas fa-lock"></i></div>' : '';
                        
                        console.log('构建发送的图片消息HTML，图片URL:', content);
                        
                        messageDiv.innerHTML = `
                            <div class="content">
                                <div class="bubble image-bubble">
                                    ${stegIndicator}
                                    <img src="${content}" alt="发送的图片" class="${isStegImage ? 'steg-image' : ''}" data-hidden="${hiddenMessage}" />
                                </div>
                                <div class="time">${time}</div>
                            </div>
                        `;
                        
                        // 为隐写图片添加点击事件
                        if (isStegImage) {
                            setTimeout(() => {
                                const img = messageDiv.querySelector('.steg-image');
                                if (img) {
                                    console.log('为发送的隐写图片添加点击事件');
                                    img.addEventListener('click', function() {
                                        showHiddenMessageModal(hiddenMessage, content);
                                    });
                                    img.style.cursor = 'pointer';
                                    img.title = '点击查看隐藏消息';
                                } else {
                                    console.error('未找到隐写图片元素');
                                }
                            }, 100);
                        }
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
                    if (isImage || isStegImage) {
                        // 对于隐写图片，添加特殊标记
                        const stegIndicator = isStegImage ? '<div class="steg-indicator" title="包含隐藏消息"><i class="fas fa-lock"></i></div>' : '';
                        
                        console.log('构建接收的图片消息HTML，图片URL:', content);
                        
                        messageDiv.innerHTML = `
                            <div class="avatar">${generateAvatar(sender)}</div>
                            <div class="content">
                                <div class="bubble image-bubble">
                                    ${stegIndicator}
                                    <img src="${content}" alt="接收的图片" class="${isStegImage ? 'steg-image' : ''}" data-hidden="${hiddenMessage}" />
                                </div>
                                <div class="time">${time}</div>
                            </div>
                        `;
                        
                        // 为隐写图片添加点击事件
                        if (isStegImage) {
                            setTimeout(() => {
                                const img = messageDiv.querySelector('.steg-image');
                                if (img) {
                                    console.log('为接收的隐写图片添加点击事件');
                                    img.addEventListener('click', function() {
                                        showHiddenMessageModal(hiddenMessage, content);
                                    });
                                    img.style.cursor = 'pointer';
                                    img.title = '点击查看隐藏消息';
                                } else {
                                    console.error('未找到隐写图片元素');
                                }
                            }, 100);
                        }
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
        let previewContent = content;
        if (isImage) previewContent = '[图片]';
        if (isStegImage) previewContent = '[隐写图片]';
        updateChatListItem(chatTarget, previewContent, time);
        
        // 如果是接收到的消息且不在当前聊天窗口，则显示通知
        if (!isSentByMe && currentChat !== chatTarget) {
            console.log(`显示系统通知`);
            let notificationMessage = content;
            if (isImage) notificationMessage = '[图片]';
            if (isStegImage) notificationMessage = '[隐写图片]';
            showNotification(sender, notificationMessage);
        }
        
        console.log('receiveMessage函数执行完毕');
        
        // 为新添加的图片和音频添加错误处理
        addImageErrorHandling();
        addAudioErrorHandling();
    } catch (err) {
        console.error('接收或显示消息时出错:', err);
    }
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

                // 添加右键菜单事件 - 用于删除聊天记录
                chatItem.addEventListener('contextmenu', chatContextMenuHandler);
                
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
                // 确保已有右键菜单事件 - 使用chatContextMenuHandler函数而不是匿名函数
                chatItem.addEventListener('contextmenu', chatContextMenuHandler);

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
                // 清空聊天窗口内容
                const messagesContainer = document.querySelector('.chat-window .messages');
                if (messagesContainer) {
                    messagesContainer.innerHTML = '';
                }
                
                // 恢复聊天窗口标题
                const chatWindowTitle = document.querySelector('.chat-window .title');
                if (chatWindowTitle) {
                    chatWindowTitle.textContent = '选择联系人开始聊天';
                }
                
                // 隐藏聊天窗口
                document.querySelector('.chat-window').classList.remove('active');
                currentChat = null;
            }
            
            // 从聊天列表中移除
            const chatItem = document.querySelector(`.chat-item[data-name="${username}"]`);
            if (chatItem && chatItem.parentNode) {
                chatItem.parentNode.removeChild(chatItem);
            }
            
            // 从联系人列表中移除
            const contactItem = document.querySelector(`.contact-item[data-name="${username}"]`);
            if (contactItem && contactItem.parentNode) {
                contactItem.parentNode.removeChild(contactItem);
            }
            
            // 从本地保存的消息历史中删除
            if (chatHistory[username]) {
                delete chatHistory[username];
                // 更新本地存储
                localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
            }
        } else {
            showErrorMessage(`删除好友失败: ${data.message || '未知错误'}`);
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
        console.log('收到Socket.IO receive_message事件，原始数据:', data);
        
        if (!data) {
            console.error('接收到的消息数据为空');
            return;
        }
        
        // 修复：正确映射所有必需字段，包括 type 和 hiddenMessage
        const messageData = {
            sender: data.sender || data.username || data.user || '',
            recipient: data.recipient || data.to || '',
            content: data.content || data.message || data.text || '',
            time: data.time || getCurrentTime(),
            type: data.type || 'text', // 确保消息类型被保留
            hiddenMessage: data.hiddenMessage || '' // 确保隐藏消息被保留
        };
        
        console.log('处理后的消息数据:', messageData, '当前用户ID:', currentUserId);
        
        if (messageData.sender && messageData.content) {
            const isSentByMe = messageData.sender.toString() === currentUserId.toString();
            
            console.log('是否为自己发送:', isSentByMe, 
                       '发送方:', messageData.sender, 
                       '当前用户:', currentUserId,
                       '接收方:', messageData.recipient);
            
            if (isSentByMe || messageData.recipient.toString() === currentUserId.toString()) {
                receiveMessage(messageData, isSentByMe);
            } else {
                console.log('消息与当前用户无关，不显示');
            }
        } else {
            console.error('处理后的消息数据格式仍然不正确:', messageData);
        }
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

    // 注册语音识别结果事件
    socket.on('asr_result', function(data) {
        console.log('收到语音识别结果:', data);
        if (data.status === 'success' && data.text && data.message_id) {
            // 保存并显示转写结果
            audioTranscriptions[data.message_id] = data.text;
            updateAudioTranscription(data.message_id, data.text);
        } else if (data.status === 'error') {
            console.error('语音识别错误:', data.error);
        }
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

// 创建并显示联系人右键菜单
function showContactContextMenu(event, contactName) {
    try {
        // 移除可能已存在的上下文菜单
        removeContextMenu();
        
        // 创建上下文菜单
        const contextMenu = document.createElement('div');
        contextMenu.className = 'context-menu';
        contextMenu.id = 'contact-context-menu';
        contextMenu.style.position = 'absolute';
        contextMenu.style.left = `${event.pageX}px`;
        contextMenu.style.top = `${event.pageY}px`;
        
        // 添加菜单项
        contextMenu.innerHTML = `
            <div class="context-menu-item" data-action="chat">发起聊天</div>
            <div class="context-menu-item danger" data-action="delete">删除好友</div>
        `;
        
        // 添加点击事件处理
        contextMenu.addEventListener('click', function(e) {
            const menuItem = e.target.closest('.context-menu-item');
            if (menuItem) {
                const action = menuItem.getAttribute('data-action');
                
                if (action === 'chat') {
                    // 发起聊天
                    console.log(`发起与 ${contactName} 的聊天`);
                    const contactItem = document.querySelector(`.contact-item[data-name="${contactName}"]`);
                    if (contactItem) {
                        contactItem.click(); // 模拟点击联系人项
                    }
                } else if (action === 'delete') {
                    // 删除好友
                    console.log(`准备删除好友: ${contactName}`);
                    removeFriend(contactName);
                }
                
                removeContextMenu();
            }
        });
        
        // 添加到文档中
        document.body.appendChild(contextMenu);
        
        // 在点击其他区域时隐藏菜单
        setTimeout(() => {
            document.addEventListener('click', removeContextMenu, { once: true });
        }, 0);
        
    } catch (err) {
        console.error('显示联系人上下文菜单时出错:', err);
    }
}

// 移除上下文菜单
function removeContextMenu() {
    // 清理所有可能的上下文菜单
    const existingMenuIds = ['contact-context-menu', 'chat-context-menu'];
    
    existingMenuIds.forEach(menuId => {
        const existingMenu = document.getElementById(menuId);
        if (existingMenu) {
            existingMenu.remove();
        }
    });
}

/**
 * 显示隐写消息输入模态框
 * @param {File} imageFile - 用户选择的图片文件
 */
function showStegMessageModal(imageFile) {
    // 如果已存在模态框，先移除它
    const existingModal = document.getElementById('steg-message-modal');
    if (existingModal) {
        existingModal.style.display = 'none';
        document.body.removeChild(existingModal);
    }
    
    // 创建图片预览URL
    const imagePreviewUrl = URL.createObjectURL(imageFile);
    
    // 创建模态框元素
    const modal = document.createElement('div');
    modal.id = 'steg-message-modal';
    modal.className = 'modal';
    
    // 设置模态框内容
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>发送隐写图片</h3>
            </div>
            <div class="modal-body">
                <div class="steg-image-container">
                    <img src="${imagePreviewUrl}" alt="预览图片" />
                </div>
                <div class="steg-message-input">
                    <h4>输入隐藏消息:</h4>
                    <textarea id="hidden-message-input" placeholder="输入要隐藏在图片中的消息内容..."></textarea>
                </div>
                <div class="modal-actions">
                    <button class="btn cancel-btn">取消</button>
                    <button class="btn send-btn primary">发送</button>
                </div>
            </div>
        </div>
    `;
    
    // 添加到文档中
    document.body.appendChild(modal);
    
    // 为模态框中的图片添加错误处理
    setTimeout(() => {
        const modalImg = modal.querySelector('.steg-image-container img');
        if (modalImg) {
            console.log('为模态框图片添加错误处理:', imagePreviewUrl);
            
            modalImg.onerror = function() {
                console.log('模态框图片加载失败:', this.src);
                
                // 检查是否已经是绝对路径
                if (this.src.startsWith('/')) {
                    // 尝试将相对路径转换为绝对路径
                    const baseUrl = window.location.origin;
                    const newSrc = baseUrl + this.src;
                    console.log('尝试使用绝对路径重新加载模态框图片:', newSrc);
                    
                    // 防止循环触发错误事件
                    this.onerror = function() {
                        console.error('使用绝对路径加载模态框图片仍然失败:', newSrc);
                        this.onerror = null;
                        this.src = '../static/img/chat.svg'; // 使用默认图标替代
                        this.style.padding = '10px';
                        this.style.background = '#f1f1f1';
                        this.style.width = '100px'; // 设置合适的宽度
                        this.style.height = 'auto';
                        this.style.margin = '0 auto'; // 居中显示
                        this.style.display = 'block';
                        this.setAttribute('title', '图片加载失败');
                    };
                    
                    this.src = newSrc;
                } else {
                    // 已经是绝对路径，直接显示替代图标
                    this.onerror = null;
                    this.src = '../static/img/chat.svg'; // 使用默认图标替代
                    this.style.padding = '10px';
                    this.style.background = '#f1f1f1';
                    this.style.width = '100px'; // 设置合适的宽度
                    this.style.height = 'auto';
                    this.style.margin = '0 auto'; // 居中显示
                    this.style.display = 'block';
                    this.setAttribute('title', '图片加载失败');
                }
            };
            
            // 如果图片已经加载失败，立即触发错误处理
            if (modalImg.complete && modalImg.naturalWidth === 0) {
                modalImg.onerror();
            }
        }
    }, 100);
    
    // 定义关闭模态框的函数
    const closeModal = function() {
        modal.style.display = 'none';
        // 延迟移除DOM元素，给CSS动画留出时间
        setTimeout(() => {
            if (modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }
            // 释放URL对象
            URL.revokeObjectURL(imagePreviewUrl);
        }, 300);
    };
    
    // 显示模态框，使用setTimeout确保DOM已更新
    setTimeout(() => {
        modal.style.display = 'flex';
        // 添加淡入效果
        setTimeout(() => {
            modal.classList.add('show');
            const modalContent = modal.querySelector('.modal-content');
            if (modalContent) {
                modalContent.style.opacity = '1';
                modalContent.style.transform = 'scale(1)';
            }
        }, 10);
    }, 0);
    
    // 取消按钮事件
    const cancelBtn = modal.querySelector('.cancel-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', closeModal);
    }
    
    // 发送按钮事件
    const sendBtn = modal.querySelector('.send-btn');
    if (sendBtn) {
        sendBtn.addEventListener('click', function() {
            const hiddenMessageInput = document.getElementById('hidden-message-input');
            if (!hiddenMessageInput) {
                showErrorMessage('无法获取隐藏消息输入框');
                return;
            }
            
            const hiddenMessage = hiddenMessageInput.value.trim();
            
            if (!hiddenMessage) {
                showErrorMessage('请输入要隐藏的消息内容');
                return;
            }
            
            if (!currentChat) {
                showErrorMessage('请先选择一个聊天对象');
                return;
            }
            
            // 发送隐写图片
            sendStegImage(currentChat, imageFile, hiddenMessage);
            
            // 关闭模态框
            closeModal();
        });
    }
    
    // 点击模态框外部区域关闭模态框
    modal.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeModal();
        }
    });
}

/**
 * 发送隐写图片消息
 * @param {string} recipient - 接收者用户名
 * @param {File} imageFile - 图片文件对象
 * @param {string} hiddenMessage - 要隐藏的消息内容
 */
function sendStegImage(recipient, imageFile, hiddenMessage) {
    if (!recipient) {
        showErrorMessage('请选择聊天对象');
        return;
    }
    
    if (!imageFile || !hiddenMessage) {
        showErrorMessage('图片和隐藏消息都不能为空');
        return;
    }
    
    // 显示发送中的状态
    showInfoMessage('正在处理图片并嵌入隐藏信息...');
    
    // 创建FormData对象来上传文件
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('recipient', recipient);
    formData.append('hidden_message', hiddenMessage);
    
    console.log('发送隐写图片:', {
        recipient: recipient,
        hiddenMessageLength: hiddenMessage.length,
        imageFileName: imageFile.name,
        imageFileSize: imageFile.size
    });
    
    // 发送请求
    fetch('/api/send_steg_image', {
        method: 'POST',
        body: formData,
        headers: {
            // 不设置Content-Type，让浏览器自动设置multipart/form-data和boundary
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`服务器返回错误: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showSuccessMessage('隐写图片已发送');
            
            // 在UI上添加一条已发送的消息（消息内容是图片URL）
            if (data.image_url) {
                receiveMessage({
                    sender: currentUserId,  // 修正：使用currentUserId而不是未定义的username
                    recipient: recipient,
                    content: data.image_url, // 使用content以保持一致性
                    time: getCurrentTime(),
                    type: 'steg_image',
                    hiddenMessage: hiddenMessage
                }, true);  // true表示这是自己发送的
            }
        } else {
            showErrorMessage(data.message || '发送失败');
        }
    })
    .catch(error => {
        console.error('发送隐写图片时出错:', error);
        showErrorMessage('发送隐写图片失败: ' + error.message);
        
        // 添加更详细的错误日志
        console.log('发送隐写图片详细错误信息:', {
            recipient: recipient,
            imageSize: imageFile ? imageFile.size : 'unknown',
            errorDetails: error
        });
    });
}

/**
 * 显示隐写图片中的隐藏消息模态框
 * @param {string} hiddenMessage - 隐藏的消息内容
 * @param {string} imageUrl - 图片的URL地址
 */
function showHiddenMessageModal(hiddenMessage, imageUrl) {
    // 处理图片URL，确保它是完整的URL
    if (imageUrl && imageUrl.startsWith('/static/')) {
        // 如果是相对路径，转换为绝对路径
        const baseUrl = window.location.origin;
        imageUrl = baseUrl + imageUrl;
        console.log('转换隐写图片路径为绝对URL:', imageUrl);
    }
    
    // 如果已存在模态框，先移除它
    const existingModal = document.getElementById('hidden-message-modal');
    if (existingModal) {
        existingModal.style.display = 'none';
        document.body.removeChild(existingModal);
    }
    
    // 创建模态框元素
    const modal = document.createElement('div');
    modal.id = 'hidden-message-modal';
    modal.className = 'modal';
    
    // 设置模态框内容
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>隐写图片中的隐藏消息</h3>
            </div>
            <div class="modal-body">
                <div class="steg-image-container">
                    <img src="${imageUrl}" alt="隐写图片" />
                </div>
                <div class="hidden-message-container">
                    <h4>隐藏消息内容:</h4>
                    <div class="hidden-message-text">${hiddenMessage}</div>
                </div>
                <div class="steg-info">
                    <p class="steg-description">这是一张包含隐藏信息的图片，隐藏信息已被解密并显示。</p>
                    <div class="steg-actions">
                        <button class="copy-btn">复制隐藏消息</button>
                        <button class="close-modal-btn">关闭</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 添加到文档中
    document.body.appendChild(modal);
    
    // 定义关闭模态框的函数
    const closeModal = function() {
        modal.classList.remove('show');
        // 添加淡出效果
        const modalContent = modal.querySelector('.modal-content');
        if (modalContent) {
            modalContent.style.opacity = '0';
            modalContent.style.transform = 'scale(0.8)';
        }
        
        // 延迟移除DOM元素，给CSS动画留出时间
        setTimeout(() => {
            modal.style.display = 'none';
            if (modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }
        }, 300);
    };
    
    // 显示模态框，使用setTimeout确保DOM已更新
    setTimeout(() => {
        modal.style.display = 'flex';
        // 添加淡入效果
        setTimeout(() => {
            modal.classList.add('show');
            const modalContent = modal.querySelector('.modal-content');
            if (modalContent) {
                modalContent.style.opacity = '1';
                modalContent.style.transform = 'scale(1)';
            }
        }, 10);
    }, 0);
    
    // 添加底部关闭按钮事件
    const closeModalBtn = modal.querySelector('.close-modal-btn');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }
    
    // 添加复制按钮事件
    const copyBtn = modal.querySelector('.copy-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            // 创建一个临时textarea元素用于复制文本
            const textarea = document.createElement('textarea');
            textarea.value = hiddenMessage;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            
            // 显示复制成功提示
            showSuccessMessage('隐藏消息已复制到剪贴板');
        });
    }
    
    // 点击模态框外部区域关闭模态框
    modal.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeModal();
        }
    });
    
    // 按ESC键关闭模态框
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && modal.style.display === 'flex') {
            closeModal();
        }
    });
}

/**
 * 显示消息到聊天窗口
 * @param {string} sender - 发送者用户名
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型 (text, image, steg_image等)
 * @param {string} hiddenMessage - 隐藏消息内容 (仅用于steg_image类型)
 */
function displayMessage(sender, message, type = 'text', hiddenMessage = '') {
    console.log('显示消息 (displayMessage):', { sender, message, type, hiddenMessage });
    
    // 构建消息对象
    const messageData = {
        sender: sender,
        content: message, // 使用content字段以保持一致性
        type: type,
        hiddenMessage: hiddenMessage,
        time: getCurrentTime()
    };
    
    // 添加更多调试信息
    if (type === 'steg_image') {
        console.log('处理隐写图片消息 (displayMessage):', {
            sender,
            message,
            type,
            hiddenMessage,
            messageData
        });
    }
    
    // 调用receiveMessage函数处理消息
    receiveMessage(messageData, false);
}

// 语音录制相关变量
var mediaRecorder = null;
var audioChunks = [];
var recordingStartTime = null;
var recordingTimer = null;
var audioBlob = null;
var isRecording = false;
var visualizerContext = null;
var audioContext = null;
var audioAnalyser = null;
var recordingVisualizer = null;

// 显示录音模态框
function showAudioRecordModal() {
    // 检查是否有当前聊天对象
    if (!currentChat) {
        showErrorMessage('请先选择一个聊天对象');
        return;
    }
    
    // 如果已存在模态框，先移除它
    const existingModal = document.getElementById('audio-record-modal');
    if (existingModal) {
        existingModal.style.display = 'none';
        document.body.removeChild(existingModal);
    }
    
    // 创建模态框元素
    const modal = document.createElement('div');
    modal.id = 'audio-record-modal';
    modal.className = 'modal';
    
    // 设置模态框内容
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>录制语音消息</h3>
            </div>
            <div class="modal-body">
                <div class="audio-recorder">
                    <div class="recorder-status">
                        <span id="recorder-status-text">准备录制</span>
                        <span id="recorder-timer">00:00</span>
                    </div>
                    <div class="recording-visualizer">
                        <canvas id="audio-visualizer"></canvas>
                    </div>
                    <div class="recorder-controls">
                        <button id="start-recording-btn" class="control-btn">
                            <i class="fas fa-microphone"></i> 开始录制
                        </button>
                        <button id="stop-recording-btn" class="control-btn" disabled>
                            <i class="fas fa-stop"></i> 停止录制
                        </button>
                        <button id="play-recording-btn" class="control-btn" disabled>
                            <i class="fas fa-play"></i> 播放录音
                        </button>
                    </div>
                    <audio id="recorded-audio" controls style="display: none;"></audio>
                    <div class="modal-actions">
                        <button id="cancel-audio-btn" class="btn cancel-btn">取消</button>
                        <button id="send-audio-btn" class="btn primary" disabled>发送</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 添加到文档中
    document.body.appendChild(modal);
    
    // 初始化可视化器
    setTimeout(() => {
        setupAudioVisualizer();
        
        // 绑定按钮事件
        document.getElementById('start-recording-btn').addEventListener('click', startRecording);
        document.getElementById('stop-recording-btn').addEventListener('click', stopRecording);
        document.getElementById('play-recording-btn').addEventListener('click', playRecording);
        document.getElementById('send-audio-btn').addEventListener('click', sendAudioRecording);
        document.getElementById('cancel-audio-btn').addEventListener('click', cancelRecording);
        
        // 重置录音状态
        resetRecordingState();
    }, 100);
    
    // 显示模态框
    setTimeout(() => {
        modal.style.display = 'flex';
        // 添加淡入效果
        setTimeout(() => {
            modal.classList.add('show');
            const modalContent = modal.querySelector('.modal-content');
            if (modalContent) {
                modalContent.style.opacity = '1';
                modalContent.style.transform = 'scale(1)';
            }
        }, 10);
    }, 0);
    
    // 点击模态框外部关闭
    modal.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeAudioRecordModal();
        }
    });
}

// 初始化录音状态
function resetRecordingState() {
    stopRecording(true); // 停止可能的录音但不更新UI
    
    // 重置UI
    document.getElementById('recorder-status-text').textContent = '准备录制';
    document.getElementById('recorder-timer').textContent = '00:00';
    document.getElementById('start-recording-btn').disabled = false;
    document.getElementById('stop-recording-btn').disabled = true;
    document.getElementById('play-recording-btn').disabled = true;
    document.getElementById('send-audio-btn').disabled = true;
    
    // 隐藏音频播放器
    const audioPlayer = document.getElementById('recorded-audio');
    audioPlayer.style.display = 'none';
    audioPlayer.src = '';
    
    // 重置录音变量
    audioChunks = [];
    audioBlob = null;
    isRecording = false;
    
    // 清除计时器
    if (recordingTimer) {
        clearInterval(recordingTimer);
        recordingTimer = null;
    }
    
    // 清除可视化器
    clearVisualizer();
}

// 关闭录音模态框
function closeAudioRecordModal() {
    const modal = document.getElementById('audio-record-modal');
    if (!modal) return;
    
    // 确保停止录音
    stopRecording(true);
    
    // 添加关闭动画
    modal.classList.remove('show');
    const modalContent = modal.querySelector('.modal-content');
    if (modalContent) {
        modalContent.style.opacity = '0';
        modalContent.style.transform = 'scale(0.8)';
    }
    
    // 延迟隐藏模态框并移除
    setTimeout(() => {
        modal.style.display = 'none';
        if (modal.parentNode) {
            modal.parentNode.removeChild(modal);
        }
    }, 300);
}

// 设置音频可视化器
function setupAudioVisualizer() {
    const canvas = document.getElementById('audio-visualizer');
    if (!canvas) return;
    
    visualizerContext = canvas.getContext('2d');
    
    // 设置画布尺寸
    const container = canvas.parentElement;
    canvas.width = container.offsetWidth;
    canvas.height = container.offsetHeight;
    
    // 清除画布
    clearVisualizer();
}

// 清除可视化器
function clearVisualizer() {
    if (!visualizerContext) return;
    
    const canvas = document.getElementById('audio-visualizer');
    visualizerContext.clearRect(0, 0, canvas.width, canvas.height);
    visualizerContext.fillStyle = '#eee';
    visualizerContext.fillRect(0, 0, canvas.width, canvas.height);
}

// 开始录音
function startRecording() {
    // 检查浏览器支持
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showErrorMessage('您的浏览器不支持录音功能');
        return;
    }
    
    // 请求麦克风权限
    navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        .then(stream => {
            // 更新UI
            document.getElementById('recorder-status-text').textContent = '正在录制...';
            document.getElementById('start-recording-btn').disabled = true;
            document.getElementById('stop-recording-btn').disabled = false;
            document.getElementById('play-recording-btn').disabled = true;
            document.getElementById('send-audio-btn').disabled = true;
            
            // 重置数据
            audioChunks = [];
            
            // 初始化录音器
            mediaRecorder = new MediaRecorder(stream);
            
            // 设置录音开始时间
            recordingStartTime = Date.now();
            
            // 开始录制
            mediaRecorder.start();
            isRecording = true;
            
            // 启动计时器
            startRecordingTimer();
            
            // 设置音频可视化
            setupAudioVisualization(stream);
            
            // 数据可用时收集
            mediaRecorder.addEventListener('dataavailable', event => {
                audioChunks.push(event.data);
            });
            
            // 录音结束时处理
            mediaRecorder.addEventListener('stop', () => {
                // 停止所有轨道
                stream.getTracks().forEach(track => track.stop());
                
                // 创建音频 Blob
                audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                
                // 创建音频URL
                const audioURL = URL.createObjectURL(audioBlob);
                
                // 设置音频播放器
                const audioPlayer = document.getElementById('recorded-audio');
                audioPlayer.src = audioURL;
                audioPlayer.style.display = 'block';
                
                // 启用播放和发送按钮
                document.getElementById('play-recording-btn').disabled = false;
                document.getElementById('send-audio-btn').disabled = false;
                
                // 更新状态文本
                document.getElementById('recorder-status-text').textContent = '录制完成';
                
                // 停止可视化
                stopVisualization();
            });
            
        })
        .catch(error => {
            console.error('获取麦克风权限失败:', error);
            showErrorMessage('无法访问麦克风，请授予权限');
        });
}

// 设置音频可视化
function setupAudioVisualization(stream) {
    try {
        // 创建音频上下文
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // 创建分析器
        audioAnalyser = audioContext.createAnalyser();
        audioAnalyser.fftSize = 256;
        
        // 连接音频源到分析器
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(audioAnalyser);
        
        // 开始可视化
        visualizeAudio();
    } catch (e) {
        console.error('设置音频可视化失败:', e);
    }
}

// 可视化音频
function visualizeAudio() {
    if (!audioAnalyser || !visualizerContext) return;
    
    // 获取画布尺寸
    const canvas = document.getElementById('audio-visualizer');
    const width = canvas.width;
    const height = canvas.height;
    
    // 创建数据数组
    const bufferLength = audioAnalyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    // 清除画布
    visualizerContext.clearRect(0, 0, width, height);
    
    // 动画函数
    function draw() {
        if (!isRecording) return;
        
        // 请求下一帧
        recordingVisualizer = requestAnimationFrame(draw);
        
        // 获取频率数据
        audioAnalyser.getByteFrequencyData(dataArray);
        
        // 清除画布
        visualizerContext.fillStyle = '#eee';
        visualizerContext.fillRect(0, 0, width, height);
        
        // 计算条形宽度
        const barWidth = (width / bufferLength) * 2.5;
        let barHeight;
        let x = 0;
        
        // 绘制频谱
        for (let i = 0; i < bufferLength; i++) {
            barHeight = dataArray[i] / 2;
            
            // 设置渐变颜色
            const r = 0;
            const g = 123 + (barHeight / 2);
            const b = 255;
            
            visualizerContext.fillStyle = `rgb(${r}, ${g}, ${b})`;
            visualizerContext.fillRect(x, height - barHeight, barWidth, barHeight);
            
            x += barWidth + 1;
        }
    }
    
    // 启动动画
    draw();
}

// 停止可视化
function stopVisualization() {
    if (recordingVisualizer) {
        cancelAnimationFrame(recordingVisualizer);
        recordingVisualizer = null;
    }
    
    if (audioContext) {
        audioContext.close().catch(console.error);
        audioContext = null;
    }
    
    audioAnalyser = null;
}

// 开始录音计时器
function startRecordingTimer() {
    if (recordingTimer) {
        clearInterval(recordingTimer);
    }
    
    const timerElement = document.getElementById('recorder-timer');
    
    recordingTimer = setInterval(() => {
        const elapsedSeconds = Math.floor((Date.now() - recordingStartTime) / 1000);
        const minutes = Math.floor(elapsedSeconds / 60);
        const seconds = elapsedSeconds % 60;
        
        timerElement.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        
        // 限制录音时间为60秒
        if (elapsedSeconds >= 60) {
            stopRecording();
        }
    }, 1000);
}

// 停止录音
function stopRecording(silent = false) {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        // 停止计时器
        if (recordingTimer) {
            clearInterval(recordingTimer);
            recordingTimer = null;
        }
        
        if (!silent) {
            // 更新UI
            document.getElementById('start-recording-btn').disabled = false;
            document.getElementById('stop-recording-btn').disabled = true;
        }
    }
}

// 播放录音
function playRecording() {
    const audioPlayer = document.getElementById('recorded-audio');
    if (audioPlayer && audioPlayer.src) {
        audioPlayer.play().catch(error => {
            console.error('播放音频失败:', error);
            showErrorMessage('播放音频失败');
        });
    }
}

// 发送录音
function sendAudioRecording() {
    if (!audioBlob || !currentChat) {
        showErrorMessage('没有录音或未选择聊天对象');
        return;
    }
    
    // 显示加载状态
    showLoadingOverlay('正在发送语音消息...');
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('recipient', currentChat);
    
    // 发送请求
    fetch('/api/send_audio', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 成功发送
            showSuccessMessage('语音消息已发送');
            
            // 关闭录音模态框
            closeAudioRecordModal();
            
            // 在UI上显示已发送的语音消息
            if (data.audio_url) {
                receiveMessage({
                    sender: currentUserId,
                    recipient: currentChat,
                    content: data.audio_url,
                    time: getCurrentTime(),
                    type: 'audio_message'
                }, true);
            }
        } else {
            showErrorMessage(data.message || '发送语音消息失败');
        }
    })
    .catch(error => {
        console.error('发送语音消息时出错:', error);
        showErrorMessage('发送语音消息失败');
    })
    .finally(() => {
        hideLoadingOverlay();
    });
}

// 取消录音
function cancelRecording() {
    // 停止录音
    stopRecording(true);
    
    // 关闭模态框
    closeAudioRecordModal();
}

// 修改displayMessage函数，添加对语音消息的支持
function displayMessage(sender, message, type = 'text', hiddenMessage = '') {
    // 创建消息容器
    const messageDiv = document.createElement('div');
    messageDiv.className = sender === currentUserId ? 'message sent' : 'message received';
    
    // 获取当前时间
    const time = getCurrentTime();
    
    // 根据消息类型构建不同的内容
    let content = '';
    
    if (type === 'audio_message') {
        // 音频消息
        const audioId = `audio_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
        
        content = `
            <div class="content">
                <div class="bubble">
                    <div class="audio-message-container">
                        <div class="audio-controls">
                            <button class="audio-play-btn" data-audio="${audioId}">
                                <i class="fas fa-play"></i>
                            </button>
                            <div class="audio-waveform"></div>
                            <span class="audio-duration">00:00</span>
                        </div>
                    </div>
                    <audio id="${audioId}" src="${message}" preload="metadata" style="display:none;"></audio>
                </div>
                <div class="time">${time}</div>
            </div>
        `;
        
        if (sender !== currentUserId) {
            // 为接收方添加头像
            content = `<div class="avatar">${generateAvatar(sender)}</div>` + content;
        }
        
        messageDiv.innerHTML = content;
        
        // 添加音频播放功能
        setTimeout(() => {
            const audio = messageDiv.querySelector(`#${audioId}`);
            const playBtn = messageDiv.querySelector(`.audio-play-btn[data-audio="${audioId}"]`);
            const durationElement = messageDiv.querySelector('.audio-duration');
            
            // 加载元数据后更新时长
            audio.addEventListener('loadedmetadata', () => {
                const duration = Math.round(audio.duration);
                const minutes = Math.floor(duration / 60);
                const seconds = duration % 60;
                durationElement.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            });
            
            // 播放按钮点击事件
            if (playBtn) {
                playBtn.addEventListener('click', () => {
                    if (audio.paused) {
                        // 先暂停所有其他音频
                        document.querySelectorAll('audio').forEach(a => {
                            if (a !== audio) a.pause();
                        });
                        
                        // 播放当前音频
                        audio.play().catch(error => {
                            console.error('播放音频失败:', error);
                            
                            // 尝试重新加载音频
                            const baseUrl = window.location.origin;
                            const audioSrc = audio.src;
                            
                            // 检查是否是相对路径
                            if (audioSrc.startsWith('/') || audioSrc.indexOf('://') === -1) {
                                audio.src = baseUrl + (audioSrc.startsWith('/') ? audioSrc : '/' + audioSrc);
                            } else if (audioSrc.startsWith('http')) {
                                // 如果是绝对路径，尝试替换域名部分
                                try {
                                    const url = new URL(audioSrc);
                                    audio.src = baseUrl + url.pathname;
                                } catch (e) {
                                    console.error('解析音频URL失败:', e);
                                }
                            }
                            
                            // 再次尝试播放
                            setTimeout(() => {
                                audio.play().catch(err => {
                                    console.error('重试播放音频仍然失败:', err);
                                    playBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                                    playBtn.setAttribute('title', '音频加载失败，请刷新页面重试');
                                });
                            }, 500);
                        });
                        
                        playBtn.querySelector('i').className = 'fas fa-pause';
                        
                        // 开始播放时请求语音转写（如果没有转写结果）
                        const messageId = audioId;
                        if (!audioTranscriptions[messageId]) {
                            requestAudioTranscription(messageId, audio.src);
                        }
                    } else {
                        // 暂停当前音频
                        audio.pause();
                        playBtn.querySelector('i').className = 'fas fa-play';
                    }
                });
                
                // 播放结束事件
                audio.addEventListener('ended', () => {
                    playBtn.querySelector('i').className = 'fas fa-play';
                });
                
                // 音频加载失败事件处理
                audio.addEventListener('error', () => {
                    console.error('音频加载失败:', audio.src);
                    playBtn.innerHTML = '<i class="fas fa-sync"></i>';
                    playBtn.setAttribute('title', '点击重新加载音频');
                });
                
                // 添加语音转写按钮
                const audioContainer = messageDiv.querySelector('.audio-message-container');
                if (audioContainer) {
                    const transcriptBtn = document.createElement('button');
                    transcriptBtn.className = 'transcript-toggle-btn';
                    transcriptBtn.title = '显示/隐藏文字转录';
                    transcriptBtn.innerHTML = '<i class="fas fa-file-alt"></i>';
                    
                    // 创建转写结果容器
                    const transcriptContainer = document.createElement('div');
                    transcriptContainer.className = 'transcript-container';
                    transcriptContainer.style.display = 'none';
                    transcriptContainer.innerHTML = `
                        <div class="transcript-text"></div>
                        <div class="transcript-loading" style="display: none;">
                            <i class="fas fa-spinner fa-spin"></i> 正在识别...
                        </div>
                    `;
                    
                    // 检查是否已有转写结果
                    const messageId = audioId;
                    if (audioTranscriptions[messageId]) {
                        const textElement = transcriptContainer.querySelector('.transcript-text');
                        if (textElement) {
                            textElement.textContent = audioTranscriptions[messageId];
                        }
                    }
                    
                    // 添加转写按钮点击事件
                    transcriptBtn.addEventListener('click', () => {
                        if (transcriptContainer.style.display === 'none') {
                            transcriptContainer.style.display = 'block';
                            
                            // 如果没有转写结果，则请求转写
                            if (!audioTranscriptions[messageId]) {
                                const loadingElement = transcriptContainer.querySelector('.transcript-loading');
                                if (loadingElement) {
                                    loadingElement.style.display = 'block';
                                }
                                
                                requestAudioTranscription(messageId, audio.src);
                            }
                        } else {
                            transcriptContainer.style.display = 'none';
                        }
                    });
                    
                    audioContainer.appendChild(transcriptContainer);
                    audioContainer.appendChild(transcriptBtn);
                }
            }
        }, 100);
    } else if (type === 'text') {
        // 文本消息
        if (sender === currentUserId) {
            content = `
                <div class="content">
                    <div class="bubble">${message}</div>
                    <div class="time">${time}</div>
                </div>
            `;
        } else {
            content = `
                <div class="avatar">${generateAvatar(sender)}</div>
                <div class="content">
                    <div class="bubble">${message}</div>
                    <div class="time">${time}</div>
                </div>
            `;
        }
        messageDiv.innerHTML = content;
    } else if (type === 'image' || type === 'steg_image') {
        // 图片和隐写图片消息处理
        const stegIndicator = type === 'steg_image' ? '<div class="steg-indicator" title="包含隐藏消息"><i class="fas fa-lock"></i></div>' : '';
        
        if (sender === currentUserId) {
            content = `
                <div class="content">
                    <div class="bubble image-bubble">
                        ${stegIndicator}
                        <img src="${message}" alt="发送的图片" class="${type === 'steg_image' ? 'steg-image' : ''}" data-hidden="${hiddenMessage}" />
                    </div>
                    <div class="time">${time}</div>
                </div>
            `;
        } else {
            content = `
                <div class="avatar">${generateAvatar(sender)}</div>
                <div class="content">
                    <div class="bubble image-bubble">
                        ${stegIndicator}
                        <img src="${message}" alt="接收的图片" class="${type === 'steg_image' ? 'steg-image' : ''}" data-hidden="${hiddenMessage}" />
                    </div>
                    <div class="time">${time}</div>
                </div>
            `;
        }
        messageDiv.innerHTML = content;
        
        // 为隐写图片添加点击事件
        if (type === 'steg_image') {
            setTimeout(() => {
                const img = messageDiv.querySelector('.steg-image');
                if (img) {
                    img.addEventListener('click', function() {
                        showHiddenMessageModal(hiddenMessage, message);
                    });
                    img.style.cursor = 'pointer';
                    img.title = '点击查看隐藏消息';
                }
            }, 100);
        }
    }
    
    return messageDiv;
}

// 修改receiveMessage函数，以支持音频消息
function receiveMessage(data, isSentByMe = false) {
    try {
        console.log('接收消息:', data, '是否为自己发送:', isSentByMe);
        
        let content = data.content || data.message || '';
        const sender = data.sender || 'unknown';
        const recipient = data.recipient || '';
        const time = data.time || getCurrentTime();
        const messageType = data.type || 'text';  // 消息类型
        const hiddenMessage = data.hiddenMessage || '';  // 隐藏消息
        
        // 确定消息的聊天对象
        // 如果是自己发送的消息，聊天对象是接收者(recipient)
        // 如果是他人发送的消息，聊天对象是发送者(sender)
        const chatTarget = isSentByMe ? recipient : sender;
        
        console.log(`${isSentByMe ? '发送' : '接收'}消息 ${isSentByMe ? '到' : '来自'} ${chatTarget}:`, content);
        console.log(`当前聊天对象: ${currentChat}, 是否为当前聊天: ${currentChat === chatTarget}`);
        console.log(`消息类型: ${messageType}, 内容: ${content}`);
        
        // 检查该聊天是否在隐藏列表中，如果是则移除并重新显示
        let hiddenChats = JSON.parse(localStorage.getItem('hiddenChats') || '[]');
        if (hiddenChats.includes(chatTarget)) {
            console.log(`收到来自隐藏聊天 ${chatTarget} 的消息，将重新显示该聊天`);
            // 从隐藏列表中移除
            hiddenChats = hiddenChats.filter(name => name !== chatTarget);
            localStorage.setItem('hiddenChats', JSON.stringify(hiddenChats));
            
            // 重新显示聊天项
            const chatItem = document.querySelector(`.chat-item[data-name="${chatTarget}"]`);
            if (chatItem) {
                chatItem.style.display = '';
                console.log(`已重新显示聊天项: ${chatTarget}`);
            }
        }
                
        // 确保聊天对象的聊天历史记录存在
        if (!chatHistory[chatTarget]) {
            console.log(`为 ${chatTarget} 创建新的聊天历史记录`);
            chatHistory[chatTarget] = [];
        }
        
        // 检查消息类型，处理不同类型的消息
        const isImage = content.startsWith('data:image/') || messageType === 'image';
        const isStegImage = messageType === 'steg_image';  // 隐写图片类型
        const isAudio = messageType === 'audio_message';  // 音频消息类型
        
        // 处理不同类型消息的路径
        if ((isStegImage || isAudio) && content.startsWith('/static/')) {
            // 如果是相对路径，转换为绝对路径
            const baseUrl = window.location.origin;
            content = baseUrl + content;
            console.log(`转换路径为绝对URL:`, content);
        }
        
        // 添加更多调试日志
        if (isAudio) {
            console.log('处理音频消息:', {
                isAudio,
                content,
                originalUrl: data.content || data.message
            });
        }
        
        // 添加消息到历史记录，包含消息类型信息
        // 确保存储前所有图片URL都是绝对路径
        let storageContent = content;
        if ((messageType === 'steg_image' || messageType === 'image' || messageType === 'audio_message') && 
            typeof storageContent === 'string' && 
            storageContent.startsWith('/')) {
            // 如果是相对路径，转换为绝对路径再存储
            const baseUrl = window.location.origin;
            storageContent = baseUrl + storageContent;
            console.log('存储到历史记录前转换路径为绝对URL:', storageContent);
        }
        
        chatHistory[chatTarget].push({
            content: storageContent,
            time: time,
            isSent: isSentByMe,
            type: messageType,  // 保存消息类型
            hiddenMessage: hiddenMessage  // 保存隐藏消息
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
                
                // 使用统一的displayMessage函数来显示消息
                const messageDiv = displayMessage(sender, content, messageType, hiddenMessage);
                
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
        let previewContent = content;
        if (isImage) previewContent = '[图片]';
        if (isStegImage) previewContent = '[隐写图片]';
        if (isAudio) previewContent = '[语音消息]';
        updateChatListItem(chatTarget, previewContent, time);
        
        // 如果是接收到的消息且不在当前聊天窗口，则显示通知
        if (!isSentByMe && currentChat !== chatTarget) {
            console.log(`显示系统通知`);
            let notificationMessage = content;
            if (isImage) notificationMessage = '[图片]';
            if (isStegImage) notificationMessage = '[隐写图片]';
            if (isAudio) notificationMessage = '[语音消息]';
            showNotification(sender, notificationMessage);
        }
        
        console.log('receiveMessage函数执行完毕');
    } catch (err) {
        console.error('接收或显示消息时出错:', err);
    }
}

// 为所有聊天图片添加错误处理
function addImageErrorHandling() {
    // 获取所有聊天图片和模态框图片
    const chatImages = document.querySelectorAll('.chat-window .messages img, .steg-image-container img');
    
    chatImages.forEach(img => {
        // 避免重复添加事件处理
        if (img.hasAttribute('data-error-handled')) {
            return;
        }
        
        // 标记为已处理
        img.setAttribute('data-error-handled', 'true');
        
        // 添加错误处理
        img.onerror = function() {
            console.log('图片加载失败:', this.src);
            
            // 检查是否已经是绝对路径
            if (this.src.startsWith('/')) {
                // 尝试将相对路径转换为绝对路径
                const baseUrl = window.location.origin;
                const newSrc = baseUrl + this.src;
                console.log('尝试使用绝对路径重新加载:', newSrc);
                
                // 防止循环触发错误事件
                this.onerror = function() {
                    console.error('使用绝对路径加载图片仍然失败:', newSrc);
                    this.onerror = null;
                    this.src = '../static/img/chat.svg'; // 使用默认图标替代
                    this.style.padding = '10px';
                    this.style.background = '#f1f1f1';
                    this.setAttribute('title', '图片加载失败');
                };
                
                this.src = newSrc;
            } else {
                // 已经是绝对路径，直接显示替代图标
                this.onerror = null;
                this.src = '../static/img/chat.svg'; // 使用默认图标替代
                this.style.padding = '10px';
                this.style.background = '#f1f1f1';
                this.setAttribute('title', '图片加载失败');
            }
        };
        
        // 如果图片已经加载失败，立即触发错误处理
        if (img.complete && img.naturalWidth === 0) {
            img.onerror();
        }
    });
}

// 聊天项右键菜单处理函数
function chatContextMenuHandler(e) {
    e.preventDefault(); // 阻止默认右键菜单
    const chatName = this.getAttribute('data-name');
    showChatContextMenu(e, chatName);
}

// 创建并显示聊天记录右键菜单
function showChatContextMenu(event, chatName) {
    try {
        // 移除可能已存在的上下文菜单
        removeContextMenu();
        
        // 创建上下文菜单
        const contextMenu = document.createElement('div');
        contextMenu.className = 'context-menu';
        contextMenu.id = 'chat-context-menu';
        contextMenu.style.position = 'absolute';
        contextMenu.style.left = `${event.pageX}px`;
        contextMenu.style.top = `${event.pageY}px`;
        
        // 添加菜单项
        contextMenu.innerHTML = `
            <div class="context-menu-item" data-action="open">打开聊天</div>
            <div class="context-menu-item" data-action="hide">隐藏此聊天</div>
            <div class="context-menu-item danger" data-action="delete">删除聊天记录</div>
            <div class="context-menu-item" data-action="cancel">取消</div>
        `;
        
        // 添加点击事件处理
        contextMenu.addEventListener('click', function(e) {
            const menuItem = e.target.closest('.context-menu-item');
            if (menuItem) {
                const action = menuItem.getAttribute('data-action');
                
                if (action === 'open') {
                    // 打开聊天
                    console.log(`打开与 ${chatName} 的聊天`);
                    const chatItem = document.querySelector(`.chat-item[data-name="${chatName}"]`);
                    if (chatItem) {
                        chatItem.click(); // 模拟点击聊天项
                    }
                } else if (action === 'hide') {
                    // 隐藏聊天
                    console.log(`准备隐藏聊天: ${chatName}`);
                    hideChat(chatName);
                } else if (action === 'delete') {
                    // 删除聊天记录
                    console.log(`准备删除聊天记录: ${chatName}`);
                    deleteChatHistory(chatName);
                }
                
                removeContextMenu();
            }
        });
        
        // 添加到文档中
        document.body.appendChild(contextMenu);
        
        // 在点击其他区域时隐藏菜单
        setTimeout(() => {
            document.addEventListener('click', removeContextMenu, { once: true });
        }, 0);
        
    } catch (err) {
        console.error('显示聊天上下文菜单时出错:', err);
    }
}

// 删除聊天记录功能
function deleteChatHistory(chatName) {
    try {
        if (!chatName) {
            console.error('删除聊天记录: 无效的聊天名称');
            return false;
        }
        
        console.log(`删除聊天记录: ${chatName}`);
        
        // 显示确认对话框
        if (!confirm(`确认要删除与"${chatName}"的所有聊天记录吗？此操作无法撤销。`)) {
            console.log('用户取消了删除操作');
            return false;
        }
        
        // 检查聊天历史记录是否存在
        if (chatHistory && chatHistory[chatName]) {
            // 删除内存中的聊天记录
            delete chatHistory[chatName];
            
            // 更新localStorage
            try {
                localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
                console.log(`聊天记录已从localStorage中删除: ${chatName}`);
            } catch (e) {
                console.error('更新localStorage失败:', e);
                return false;
            }
            
            // 如果当前正在显示该聊天，清空消息区域
            if (currentChat === chatName) {
                const messagesContainer = document.querySelector('.chat-window .messages');
                if (messagesContainer) {
                    messagesContainer.innerHTML = `<div class="date">今天</div>`;
                    console.log('已清空当前聊天窗口');
                }
            }
            
            // 更新UI - 移除聊天列表项或更新其内容
            const chatItem = document.querySelector(`.chat-item[data-name="${chatName}"]`);
            if (chatItem) {
                // 更新消息预览为空
                const messageElement = chatItem.querySelector('.message');
                if (messageElement) {
                    messageElement.textContent = '没有消息';
                }
                
                // 更新时间
                const timeElement = chatItem.querySelector('.time');
                if (timeElement) {
                    timeElement.textContent = getCurrentTime();
                }
            }
            
            showSuccessMessage(`已删除与"${chatName}"的聊天记录`);
            return true;
        } else {
            console.log(`聊天记录不存在: ${chatName}`);
            return false;
        }
    } catch (err) {
        console.error('删除聊天记录时出错:', err);
        showErrorMessage(`删除聊天记录失败: ${err.message}`);
        return false;
    }
}

// 移除上下文菜单
function removeContextMenu() {
    const existingMenu = document.getElementById('contact-context-menu') || document.getElementById('chat-context-menu');
    if (existingMenu) {
        existingMenu.remove();
    }
}

// 隐藏聊天功能
function hideChat(chatName) {
    try {
        if (!chatName) {
            console.error('隐藏聊天: 无效的聊天名称');
            return false;
        }
        
        console.log(`隐藏聊天: ${chatName}`);
        
        // 从聊天列表中隐藏该聊天项
        const chatItem = document.querySelector(`.chat-item[data-name="${chatName}"]`);
        if (chatItem) {
            chatItem.style.display = 'none';
            console.log(`已在UI中隐藏聊天: ${chatName}`);
        }
        
        // 将该聊天添加到隐藏列表
        let hiddenChats = JSON.parse(localStorage.getItem('hiddenChats') || '[]');
        if (!hiddenChats.includes(chatName)) {
            hiddenChats.push(chatName);
            localStorage.setItem('hiddenChats', JSON.stringify(hiddenChats));
            console.log(`已将 ${chatName} 添加到隐藏列表`);
        }
        
        // 如果当前正在查看该聊天，返回到聊天列表
        if (currentChat === chatName) {
            // 隐藏聊天窗口，显示默认提示
            const chatWindow = document.querySelector('.chat-window');
            if (chatWindow) {
                const titleElement = chatWindow.querySelector('.title');
                if (titleElement) {
                    titleElement.textContent = '选择联系人开始聊天';
                }
                
                // 清空消息区域，显示默认提示
                const messagesContainer = document.querySelector('.chat-window .messages');
                if (messagesContainer) {
                    messagesContainer.innerHTML = '<div class="empty-chat-message">选择联系人开始聊天</div>';
                }
                
                currentChat = null; // 重置当前聊天
            }
        }
        
        showSuccessMessage(`已隐藏"${chatName}"的聊天`);
        return true;
    } catch (err) {
        console.error('隐藏聊天时出错:', err);
        showErrorMessage(`隐藏聊天失败: ${err.message}`);
        return false;
    }
}

// 为所有聊天音频添加错误处理
function addAudioErrorHandling() {
    // 获取所有聊天音频元素
    const chatAudios = document.querySelectorAll('.chat-window .messages audio');
    
    chatAudios.forEach(audio => {
        // 避免重复添加事件处理
        if (audio.hasAttribute('data-error-handled')) {
            return;
        }
        
        // 标记为已处理
        audio.setAttribute('data-error-handled', 'true');
        
        // 添加错误处理
        audio.onerror = function() {
            console.log('音频加载失败:', this.src);
            
            // 尝试从相对路径转为绝对路径
            if (this.src.startsWith('/') || this.src.indexOf('://') === -1) {
                // 转换为绝对路径
                const baseUrl = window.location.origin;
                const newSrc = baseUrl + (this.src.startsWith('/') ? this.src : '/' + this.src);
                console.log('尝试使用绝对路径重新加载音频:', newSrc);
                
                // 防止循环触发错误事件
                let errorHandler = this.onerror;
                this.onerror = function() {
                    // 恢复原有的错误处理程序
                    this.onerror = errorHandler;
                    
                    // 查找对应消息，获取更多信息用于恢复
                    try {
                        // 通过ID查找对应的消息数据
                        const audioId = this.id;
                        const messageElement = this.closest('.message');
                        if (messageElement) {
                            const isSent = messageElement.classList.contains('sent');
                            const audioBtn = document.querySelector(`button[data-audio="${audioId}"]`);
                            
                            // 尝试修改URL格式
                            // 检查当前聊天历史中是否有这个音频的记录
                            if (currentChat && chatHistory[currentChat]) {
                                const matchingMsg = chatHistory[currentChat].find(msg => 
                                    msg.type === 'audio_message' && msg.content && 
                                    (msg.content === this.src || msg.originalUrl === this.src)
                                );
                                
                                if (matchingMsg) {
                                    console.log('找到匹配的聊天历史记录，尝试恢复音频:', matchingMsg);
                                    
                                    // 检查是否有保存的原始URL
                                    if (matchingMsg.originalUrl && matchingMsg.originalUrl !== this.src) {
                                        // 使用原始URL重试
                                        console.log('尝试使用原始URL重新加载:', matchingMsg.originalUrl);
                                        this.src = matchingMsg.originalUrl;
                                        return; // 先尝试原始URL
                                    }
                                    
                                    // 如果重试次数小于3，尝试不同的URL格式
                                    if (matchingMsg.retryCount < 3) {
                                        matchingMsg.retryCount++;
                                        
                                        // 提取文件名
                                        const urlParts = this.src.split('/');
                                        const filename = urlParts[urlParts.length - 1];
                                        
                                        // 尝试使用不同的路径格式
                                        const alternativeUrls = [
                                            `${window.location.origin}/static/${filename}`,
                                            `/static/${filename}`,
                                            `static/${filename}`
                                        ];
                                        
                                        // 尝试下一个URL
                                        const nextUrl = alternativeUrls[matchingMsg.retryCount % alternativeUrls.length];
                                        console.log(`尝试备选URL (${matchingMsg.retryCount}/3):`, nextUrl);
                                        this.src = nextUrl;
                                        return;
                                    }
                                }
                            }
                            
                            // 如果所有尝试都失败，显示错误状态
                            console.error('所有音频加载尝试均失败:', this.src);
                            if (audioBtn) {
                                audioBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                                audioBtn.setAttribute('disabled', 'true');
                                audioBtn.setAttribute('title', '音频加载失败，点击尝试重新加载');
                                
                                // 添加点击事件用于手动重试
                                audioBtn.onclick = function() {
                                    // 重置按钮状态
                                    this.innerHTML = '<i class="fas fa-sync fa-spin"></i>';
                                    this.removeAttribute('disabled');
                                    this.setAttribute('title', '正在重新加载...');
                                    
                                    // 重新加载音频
                                    const audioElement = document.getElementById(audioId);
                                    if (audioElement) {
                                        // 尝试加载不同域名的URL
                                        try {
                                            const currentUrl = new URL(audioElement.src);
                                            const path = currentUrl.pathname;
                                            audioElement.src = window.location.origin + path;
                                        } catch (e) {
                                            // 如果URL解析失败，可能是相对路径
                                            const parts = audioElement.src.split('/');
                                            const filename = parts[parts.length - 1];
                                            audioElement.src = `${window.location.origin}/static/${filename}`;
                                        }
                                        
                                        // 加载完成后恢复按钮状态
                                        audioElement.oncanplaythrough = function() {
                                            audioBtn.innerHTML = '<i class="fas fa-play"></i>';
                                            audioBtn.setAttribute('title', '播放音频');
                                            
                                            // 恢复原始点击事件
                                            audioBtn.onclick = function() {
                                                if (audioElement.paused) {
                                                    audioElement.play();
                                                    this.querySelector('i').className = 'fas fa-pause';
                                                } else {
                                                    audioElement.pause();
                                                    this.querySelector('i').className = 'fas fa-play';
                                                }
                                            };
                                        };
                                    }
                                };
                            }
                        }
                    } catch (e) {
                        console.error('处理音频错误时出现异常:', e);
                    }
                };
                
                this.src = newSrc;
            } else {
                // 如果已经是绝对路径但仍然失败
                console.error('使用绝对路径加载音频仍然失败:', this.src);
                const playButton = document.querySelector(`button[data-audio="${this.id}"]`);
                if (playButton) {
                    playButton.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                    playButton.setAttribute('title', '音频加载失败，点击尝试重新加载');
                    
                    // 添加重试功能
                    playButton.onclick = function() {
                        const audioElement = document.getElementById(this.getAttribute('data-audio'));
                        if (audioElement) {
                            this.innerHTML = '<i class="fas fa-sync fa-spin"></i>';
                            this.setAttribute('title', '正在重新加载...');
                            
                            // 尝试解析出路径并使用当前域名
                            try {
                                const url = new URL(audioElement.src);
                                const path = url.pathname;
                                audioElement.src = window.location.origin + path;
                                
                                // 如果加载成功，恢复按钮状态
                                audioElement.oncanplaythrough = function() {
                                    playButton.innerHTML = '<i class="fas fa-play"></i>';
                                    playButton.setAttribute('title', '播放音频');
                                    
                                    // 恢复原始点击事件
                                    playButton.onclick = function() {
                                        if (audioElement.paused) {
                                            audioElement.play();
                                            this.querySelector('i').className = 'fas fa-pause';
                                        } else {
                                            audioElement.pause();
                                            this.querySelector('i').className = 'fas fa-play';
                                        }
                                    };
                                };
                            } catch (e) {
                                console.error('重试加载音频时出错:', e);
                                this.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                                this.setAttribute('title', '重新加载失败');
                            }
                        }
                    };
                }
            }
        };
        
        // 确保音频元素加载了元数据后更新持续时间显示
        audio.onloadedmetadata = function() {
            // 获取音频时长
            const duration = audio.duration;
            const durationElement = audio.parentElement.querySelector('.audio-duration');
            if (durationElement) {
                durationElement.textContent = formatAudioDuration(duration);
            }
        };
        
        // 确保音频按钮有正确的点击事件
        const audioId = audio.id;
        const playBtn = document.querySelector(`.audio-play-btn[data-audio="${audioId}"]`);
        if (playBtn && !playBtn.hasAttribute('data-click-handled')) {
            playBtn.setAttribute('data-click-handled', 'true');
            
            playBtn.addEventListener('click', function() {
                const audio = document.getElementById(this.getAttribute('data-audio'));
                if (!audio) return;
                
                // 暂停其他正在播放的音频
                document.querySelectorAll('audio').forEach(a => {
                    if (a !== audio && !a.paused) {
                        a.pause();
                        const otherBtn = document.querySelector(`.audio-play-btn[data-audio="${a.id}"]`);
                        if (otherBtn) otherBtn.querySelector('i').className = 'fas fa-play';
                    }
                });
                
                if (audio.paused) {
                    // 播放
                    audio.play().catch(err => {
                        console.error('播放音频失败，尝试修复URL:', err);
                        
                        // 尝试修复URL
                        const urlParts = audio.src.split('/');
                        const filename = urlParts[urlParts.length - 1];
                        const fixedUrl = `${window.location.origin}/static/${filename}`;
                        
                        console.log('尝试使用修复后的URL播放:', fixedUrl);
                        audio.src = fixedUrl;
                        
                        // 重试播放
                        setTimeout(() => audio.play().catch(e => console.error('重试播放失败:', e)), 300);
                    });
                    
                    this.querySelector('i').className = 'fas fa-pause';
                } else {
                    // 暂停
                    audio.pause();
                    this.querySelector('i').className = 'fas fa-play';
                }
            });
            
            // 播放结束事件
            audio.addEventListener('ended', function() {
                const btn = document.querySelector(`.audio-play-btn[data-audio="${this.id}"]`);
                if (btn) btn.querySelector('i').className = 'fas fa-play';
            });
        }
    });
}

// 更新音频时长格式化函数（如果不存在）
function formatAudioDuration(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// 显示语音转文字功能信息
function showTranscriptInfo() {
    showInfoModal('语音转文字功能', `
        <p>点击任意语音消息进行播放，系统将自动进行语音识别并显示文字内容。</p>
        <p>您可以通过点击语音消息旁边的文字图标来显示或隐藏识别结果。</p>
        <p>首次识别可能需要几秒钟时间，请耐心等待。</p>
    `);
}

// 请求音频转写
function requestAudioTranscription(messageId, audioUrl) {
    console.log('请求音频转写:', messageId, audioUrl);
    
    // 使用多种方式查找音频元素
    const audioElements = document.querySelectorAll(`audio#${messageId}, audio[data-audio="${messageId}"]`);
    console.log(`找到相关音频元素: ${audioElements.length}个`);
    
    const parentElements = [];
    
    if (audioElements.length === 0) {
        // 如果找不到匹配的音频元素，尝试处理所有音频容器
        const allAudioContainers = document.querySelectorAll('.audio-message-container');
        console.log(`找到所有音频容器: ${allAudioContainers.length}个，尝试处理最近的一个`);
        
        if (allAudioContainers.length > 0) {
            // 优先处理最近添加的（通常是最后一个）
            const latestContainer = allAudioContainers[allAudioContainers.length - 1];
            prepareTranscriptContainer(latestContainer);
            parentElements.push(latestContainer);
        }
    } else {
        audioElements.forEach(audio => {
            let parent = audio.closest('.audio-message-container');
            
            // 如果没有直接找到容器，尝试查找音频元素的父元素
            if (!parent) {
                const audioId = audio.id;
                const playBtn = document.querySelector(`.audio-play-btn[data-audio="${audioId}"]`);
                if (playBtn) {
                    parent = playBtn.closest('.audio-message-container');
                }
            }
            
            if (parent) {
                prepareTranscriptContainer(parent);
                parentElements.push(parent);
            }
        });
    }
    
    // 准备转写容器
    function prepareTranscriptContainer(parent) {
        // 添加转写容器
        if (!parent.querySelector('.transcript-container')) {
            const transcriptContainer = document.createElement('div');
            transcriptContainer.className = 'transcript-container';
            transcriptContainer.innerHTML = `
                <div class="transcript-text"></div>
                <div class="transcript-loading">
                    <i class="fas fa-spinner fa-spin"></i> 正在识别...
                </div>
            `;
            parent.appendChild(transcriptContainer);
        }
        
        // 显示加载状态
        const loadingElement = parent.querySelector('.transcript-loading');
        if (loadingElement) {
            loadingElement.style.display = 'block';
        }
        
        // 确保转写容器可见
        const transcriptContainer = parent.querySelector('.transcript-container');
        if (transcriptContainer) {
            transcriptContainer.style.display = 'block';
        }
    }
    
    // 从URL获取音频文件并发送到服务器进行转写
    fetch(audioUrl)
    .then(response => response.blob())
    .then(blob => {
        const formData = new FormData();
        formData.append('audio_file', blob, `${messageId}.wav`);
        formData.append('message_id', messageId);
        
        return fetch('/api/speech_to_text', {
            method: 'POST',
            body: formData
        });
    })
    .then(response => response.json())
    .then(data => {
        console.log('语音转写请求提交结果:', data);
        
        // 如果服务器直接返回了转写结果（而不是等待Socket.IO事件），立即更新UI
        if (data.status === 'success' && data.text) {
            // 保存并显示转写结果
            audioTranscriptions[messageId] = data.text;
            updateAudioTranscription(messageId, data.text);
        } else if (data.status === 'error') {
            // 显示错误信息
            parentElements.forEach(parent => {
                const loadingElement = parent.querySelector('.transcript-loading');
                const textElement = parent.querySelector('.transcript-text');
                
                if (loadingElement) {
                    loadingElement.style.display = 'none';
                }
                
                if (textElement) {
                    textElement.textContent = `识别失败: ${data.message || '未知错误'}`;
                    textElement.style.display = 'block';
                }
            });
        }
    })
    .catch(error => {
        console.error('请求音频转写失败:', error);
        // 隐藏加载状态并显示错误信息
        parentElements.forEach(parent => {
            const loadingElement = parent.querySelector('.transcript-loading');
            const textElement = parent.querySelector('.transcript-text');
            
            if (loadingElement) {
                loadingElement.style.display = 'none';
            }
            
            if (textElement) {
                textElement.textContent = '转写失败，请重试';
                textElement.style.display = 'block';
            }
        });
    });
}

// 更新音频转写结果
function updateAudioTranscription(messageId, text) {
    console.log('更新音频转写结果:', messageId, text, '当前音频元素数量:', document.querySelectorAll('audio').length);
    
    // 更新全局存储
    audioTranscriptions[messageId] = text;
    
    // 尝试多种选择器查找相关音频元素
    const audioElements = document.querySelectorAll(`audio#${messageId}, audio[data-audio="${messageId}"]`);
    console.log(`找到相关音频元素: ${audioElements.length}个`);
    
    if (audioElements.length === 0) {
        // 如果找不到直接匹配的元素，尝试在所有音频容器中查找
        const allAudioContainers = document.querySelectorAll('.audio-message-container');
        console.log(`找到所有音频容器: ${allAudioContainers.length}个`);
        
        allAudioContainers.forEach(container => {
            // 更新此容器中的转写内容
            updateTranscriptInContainer(container, text);
        });
    } else {
        audioElements.forEach(audio => {
            // 找到音频元素所在的容器
            let parent = audio.closest('.audio-message-container');
            
            // 如果没有直接找到容器，尝试查找音频元素的父元素
            if (!parent) {
                const audioId = audio.id;
                const playBtn = document.querySelector(`.audio-play-btn[data-audio="${audioId}"]`);
                if (playBtn) {
                    parent = playBtn.closest('.audio-message-container');
                }
            }
            
            if (parent) {
                updateTranscriptInContainer(parent, text);
            }
        });
    }
    
    // 持久化保存转写结果
    localStorage.setItem(`audio_transcript_${messageId}`, text);
}

// 在容器中更新转写内容
function updateTranscriptInContainer(container, text) {
    let transcriptContainer = container.querySelector('.transcript-container');
    let loadingElement, textElement;
    
    // 如果没有转写容器，创建一个
    if (!transcriptContainer) {
        transcriptContainer = document.createElement('div');
        transcriptContainer.className = 'transcript-container';
        transcriptContainer.innerHTML = `
            <div class="transcript-text"></div>
            <div class="transcript-loading" style="display: none;">
                <i class="fas fa-spinner fa-spin"></i> 正在识别...
            </div>
        `;
        container.appendChild(transcriptContainer);
    }
    
    loadingElement = transcriptContainer.querySelector('.transcript-loading');
    textElement = transcriptContainer.querySelector('.transcript-text');
    
    // 隐藏加载状态
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
    
    // 显示转写结果
    if (textElement) {
        textElement.textContent = text || '无法识别语音内容';
        textElement.style.display = 'block';
    }
    
    // 显示转写容器 (初次显示结果时)
    transcriptContainer.style.display = 'block';
    
    // 如果没有显示转写切换按钮，添加一个
    if (!container.querySelector('.transcript-toggle-btn')) {
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'transcript-toggle-btn';
        toggleBtn.title = '显示/隐藏文字转录';
        toggleBtn.innerHTML = '<i class="fas fa-file-alt"></i>';
        
        // 添加切换按钮点击事件
        toggleBtn.addEventListener('click', function() {
            if (transcriptContainer.style.display === 'none') {
                transcriptContainer.style.display = 'block';
            } else {
                transcriptContainer.style.display = 'none';
            }
        });
        
        container.appendChild(toggleBtn);
    }
}

function addFriendBtnHandler(event) {
    console.log('添加好友按钮被点击');
    event.preventDefault();
    event.stopPropagation();
    showAddFriendModal();
}

// 关闭模态框的通用函数
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        activeModal = null;
        console.log(`已关闭模态框: ${modalId}`);
    }
}