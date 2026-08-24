// ============================================
// SESSION & USER MANAGEMENT
// ============================================
let currentUser = null;
let currentConversationId = null;
let greetingTemplateHTML = '';

const STORAGE_KEYS = {
    users: 'lawMitraUsers',
    localSessionUser: 'lawMitraUser',
    sessionUser: 'lawMitraUser'
};

const AVATAR_LIBRARY = {
    male: [
        { key: 'boy', label: 'Boy', subtitle: 'Teen / Young', url: 'https://randomuser.me/api/portraits/men/1.jpg' },
        { key: 'professional', label: 'Man', subtitle: 'Professional', url: 'https://randomuser.me/api/portraits/men/32.jpg' },
        { key: 'older', label: 'Old Man', subtitle: 'Senior', url: 'https://randomuser.me/api/portraits/men/75.jpg' }
    ],
    female: [
        { key: 'girl', label: 'Girl', subtitle: 'Teen / Young', url: 'https://randomuser.me/api/portraits/women/1.jpg' },
        { key: 'professional', label: 'Woman', subtitle: 'Professional', url: 'https://randomuser.me/api/portraits/women/44.jpg' },
        { key: 'older', label: 'Old Woman', subtitle: 'Senior', url: 'https://randomuser.me/api/portraits/women/79.jpg' }
    ]
};

function getDefaultAvatarForGender(gender) {
    const library = AVATAR_LIBRARY[gender] || AVATAR_LIBRARY.male;
    return library[0];
}

function getAvatarForUser(user) {
    if (user && user.avatarUrl) return user.avatarUrl;
    if (user && user.gender) return getDefaultAvatarForGender(user.gender).url;
    return getDefaultAvatarForGender('male').url;
}

function renderSignupAvatarOptions() {
    const genderSelect = document.getElementById('signup-gender');
    const avatarPicker = document.getElementById('avatar-picker');
    const avatarGrid = document.getElementById('avatar-grid');
    if (!genderSelect || !avatarPicker || !avatarGrid) return;
    const gender = genderSelect.value;
    if (!gender || !AVATAR_LIBRARY[gender]) {
        avatarPicker.classList.remove('visible');
        avatarGrid.innerHTML = '';
        avatarGrid.dataset.selectedAvatarUrl = '';
        avatarGrid.dataset.selectedAvatarKey = '';
        return;
    }
    const avatars = AVATAR_LIBRARY[gender];
    avatarPicker.classList.add('visible');
    avatarGrid.innerHTML = '';
    avatars.forEach((avatar, index) => {
        const option = document.createElement('button');
        option.type = 'button';
        option.className = 'avatar-option';
        option.dataset.avatarUrl = avatar.url;
        option.dataset.avatarKey = avatar.key;
        option.innerHTML = `<img src="${avatar.url}" alt="${avatar.label}"><span>${avatar.label}</span><small>${avatar.subtitle}</small>`;
        option.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.avatar-option.selected').forEach(s => s.classList.remove('selected'));
            option.classList.add('selected');
            avatarGrid.dataset.selectedAvatarUrl = avatar.url;
            avatarGrid.dataset.selectedAvatarKey = avatar.key;
        });
        if (index === 0) {
            option.classList.add('selected');
            avatarGrid.dataset.selectedAvatarUrl = avatar.url;
            avatarGrid.dataset.selectedAvatarKey = avatar.key;
        }
        avatarGrid.appendChild(option);
    });
}

function getAuthenticatedUserFromStorage() {
    return localStorage.getItem(STORAGE_KEYS.localSessionUser) || sessionStorage.getItem(STORAGE_KEYS.sessionUser);
}

function getHistoryStorageKey(username) { return `lawMitraHistory_${username}`; }

function getUserConversations() {
    if (!currentUser || !currentUser.username) return [];
    const raw = localStorage.getItem(getHistoryStorageKey(currentUser.username));
    if (!raw) return [];
    try { const p = JSON.parse(raw); return Array.isArray(p) ? p : []; } catch { return []; }
}

function saveUserConversations(conversations) {
    if (!currentUser || !currentUser.username) return;
    localStorage.setItem(getHistoryStorageKey(currentUser.username), JSON.stringify(conversations));
}

function generateConversationId() { return `${Date.now()}_${Math.random().toString(36).slice(2, 9)}`; }

function deriveConversationTitle(messages) {
    const first = messages.find(m => m.role === 'user');
    if (!first || !first.content) return 'New Conversation';
    const c = first.content.replace(/\s+/g, ' ').trim();
    return c.length > 45 ? `${c.slice(0, 45)}...` : c;
}

function getCurrentConversation() {
    if (!currentConversationId) return null;
    return getUserConversations().find(c => c.id === currentConversationId) || null;
}

function createNewConversation() {
    const conversations = getUserConversations();
    const newConv = { id: generateConversationId(), title: 'New Conversation', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), messages: [] };
    conversations.unshift(newConv);
    saveUserConversations(conversations);
    currentConversationId = newConv.id;
    renderConversationHistory();
    return newConv;
}

function resetChatAreaToGreeting() {
    const area = document.querySelector('.chat-scroll-area');
    if (area) area.innerHTML = greetingTemplateHTML || '';
}

function renderConversationHistory() {
    const historyList = document.getElementById('history-list');
    if (!historyList) return;
    const conversations = getUserConversations().slice().sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
    historyList.innerHTML = '';
    if (conversations.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'history-empty';
        empty.textContent = 'No recent chats yet. Start a conversation to see it here.';
        historyList.appendChild(empty);
        return;
    }
    conversations.forEach(conversation => {
        const item = document.createElement('div');
        item.className = 'history-item';
        if (conversation.id === currentConversationId) item.classList.add('active');
        const title = document.createElement('div');
        title.className = 'history-title';
        title.textContent = conversation.title || 'Conversation';
        const actions = document.createElement('div');
        actions.className = 'history-actions';
        const menuButton = document.createElement('button');
        menuButton.type = 'button';
        menuButton.className = 'history-menu-btn';
        menuButton.innerHTML = '<i class="fa-solid fa-ellipsis-vertical"></i>';
        const menu = document.createElement('div');
        menu.className = 'history-menu';
        const shareButton = document.createElement('button');
        shareButton.type = 'button';
        shareButton.innerHTML = '<i class="fa-solid fa-share-nodes"></i> Share';
        const deleteButton = document.createElement('button');
        deleteButton.type = 'button';
        deleteButton.className = 'danger';
        deleteButton.innerHTML = '<i class="fa-regular fa-trash-can"></i> Delete';
        item.appendChild(title);
        actions.appendChild(menuButton);
        menu.appendChild(shareButton);
        menu.appendChild(deleteButton);
        actions.appendChild(menu);
        item.appendChild(actions);
        menuButton.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.history-item.menu-open').forEach(o => { if (o !== item) o.classList.remove('menu-open'); });
            item.classList.toggle('menu-open');
        });
        shareButton.addEventListener('click', async (e) => { e.stopPropagation(); item.classList.remove('menu-open'); await shareConversation(conversation); });
        deleteButton.addEventListener('click', (e) => { e.stopPropagation(); item.classList.remove('menu-open'); deleteConversation(conversation.id); });
        item.addEventListener('click', () => { currentConversationId = conversation.id; renderConversationHistory(); renderCurrentConversationMessages(); toggleView('chat'); });
        historyList.appendChild(item);
    });
}

function deleteConversation(conversationId) {
    if (!currentUser || !conversationId) return;
    const conversations = getUserConversations().filter(c => c.id !== conversationId);
    saveUserConversations(conversations);
    if (currentConversationId === conversationId) {
        currentConversationId = conversations[0] ? conversations[0].id : null;
        if (currentConversationId) renderCurrentConversationMessages();
        else { resetChatAreaToGreeting(); showWelcomeView(); }
    }
    renderConversationHistory();
}

async function shareConversation(conversation) {
    if (!conversation || !Array.isArray(conversation.messages) || conversation.messages.length === 0) { alert('No messages to share yet.'); return; }
    const text = conversation.messages.map(m => `${m.role === 'user' ? 'You' : 'LawGuideAI'}: ${m.content}`).join('\n\n');
    if (navigator.share) {
        try { await navigator.share({ title: conversation.title || 'LawGuideAI Conversation', text }); return; }
        catch (e) { if (e && e.name === 'AbortError') return; }
    }
    try { await navigator.clipboard.writeText(text); alert('Conversation copied to clipboard.'); }
    catch { alert('Sharing is not supported in this browser.'); }
}

function renderCurrentConversationMessages() {
    const conversation = getCurrentConversation();
    resetChatAreaToGreeting();
    if (!conversation || !Array.isArray(conversation.messages)) return;
    conversation.messages.forEach(msg => addMessage(msg.content, msg.role === 'user'));
}

function appendToCurrentConversation(role, content) {
    if (!content || !currentUser) return;
    let conversations = getUserConversations();
    if (!currentConversationId) { createNewConversation(); conversations = getUserConversations(); }
    const index = conversations.findIndex(c => c.id === currentConversationId);
    if (index === -1) return;
    conversations[index].messages.push({ role, content, timestamp: new Date().toISOString() });
    conversations[index].title = deriveConversationTitle(conversations[index].messages);
    conversations[index].updatedAt = new Date().toISOString();
    const [updated] = conversations.splice(index, 1);
    conversations.unshift(updated);
    saveUserConversations(conversations);
    currentConversationId = updated.id;
    renderConversationHistory();
}

function startNewConversation() { createNewConversation(); resetChatAreaToGreeting(); toggleView('chat'); }

function toggleView(viewName) {
    const chatView = document.getElementById('chat-view');
    if (chatView) chatView.classList.remove('hidden');
}

function showWelcomeView() {
    const chatView = document.getElementById('chat-view');
    if (chatView) chatView.classList.remove('hidden');
    resetChatAreaToGreeting();
}

window.startNewConversation = startNewConversation;
window.toggleView = toggleView;
window.showWelcomeView = showWelcomeView;

function initializeUserWorkspace() {
    renderConversationHistory();
    const conversations = getUserConversations();
    if (conversations.length > 0) {
        currentConversationId = conversations[0].id;
        renderConversationHistory();
        renderCurrentConversationMessages();
        toggleView('chat');
    } else {
        startNewConversation();
    }
}

function checkAuth() {
    try {
        const user = getAuthenticatedUserFromStorage();
        if (user) { currentUser = JSON.parse(user); showMainApp(); updateUserDisplay(); initializeUserWorkspace(); }
        else showPage('landing');
    } catch (e) {
        localStorage.removeItem(STORAGE_KEYS.localSessionUser);
        sessionStorage.removeItem(STORAGE_KEYS.sessionUser);
        currentUser = null;
        showPage('landing');
    }
}

function updateUserDisplay() {
    if (currentUser) {
        document.getElementById('user-display-name').textContent = currentUser.fullname;
        const userAvatar = document.getElementById('user-avatar');
        if (userAvatar) userAvatar.src = getAvatarForUser(currentUser);
    }
}

window.showPage = function showPage(page, pushState = true) {
    const landingPage = document.getElementById('landing-page');
    const loginPage = document.getElementById('login-page');
    const signupPage = document.getElementById('signup-page');
    const mainApp = document.getElementById('main-app');
    if (!loginPage || !signupPage || !mainApp || !landingPage) return;

    if (pushState) {
        history.pushState({ page: page }, '', '#' + page);
    }

    landingPage.classList.add('hidden');
    loginPage.classList.add('hidden');
    signupPage.classList.add('hidden');
    mainApp.classList.add('hidden');
    if (page === 'landing') landingPage.classList.remove('hidden');
    else if (page === 'login') loginPage.classList.remove('hidden');
    else if (page === 'signup') signupPage.classList.remove('hidden');
    else if (page === 'app') mainApp.classList.remove('hidden');
};

window.addEventListener('popstate', function (event) {
    if (event.state && event.state.page) {
        showPage(event.state.page, false);
    } else {
        const hash = window.location.hash.replace('#', '');
        if (['landing', 'login', 'signup', 'app'].includes(hash)) {
            showPage(hash, false);
        } else {
            showPage('landing', false);
        }
    }
});

function showMainApp() {
    showPage('app');
}

window.togglePasswordVisibility = function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const icon = input.nextElementSibling;
    if (!icon) return;
    if (input.type === 'password') {
        input.type = 'text';
        const faIcon = icon.querySelector('i');
        if (faIcon) {
            faIcon.className = 'fa-regular fa-eye-slash';
        } else {
            icon.textContent = '👁️';
        }
    } else {
        input.type = 'password';
        const faIcon = icon.querySelector('i');
        if (faIcon) {
            faIcon.className = 'fa-regular fa-eye';
        } else {
            icon.textContent = '👁';
        }
    }
};

// ============================================
// MAIN DOMContentLoaded
// ============================================
document.addEventListener('DOMContentLoaded', () => {

    // Initial page load based on hash
    const initialHash = window.location.hash.replace('#', '');
    if (['landing', 'login', 'signup', 'app'].includes(initialHash)) {
        showPage(initialHash, false);
    }

    // Nav links
    document.querySelectorAll('a[onclick*="showPage"]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault(); e.stopPropagation();
            const m = link.getAttribute('onclick').match(/showPage\(['"]([^'"]+)['"]\)/);
            if (m && m[1]) window.showPage(m[1]);
        });
    });

    // ============================================
    // LOGIN
    // ============================================
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const username = document.getElementById('login-username').value.trim();
            const password = document.getElementById('login-password').value;
            const rememberMe = document.getElementById('remember-me').checked;
            const errorDiv = document.getElementById('login-error');
            let users = [];
            try { users = JSON.parse(localStorage.getItem(STORAGE_KEYS.users) || '[]'); } catch { users = []; }
            const user = Array.isArray(users) ? users.find(u => u && u.username === username && u.password === password) : null;
            if (user) {
                currentUser = { username: user.username, fullname: user.fullname, email: user.email, gender: user.gender || 'male', avatarKey: user.avatarKey || 'boy', avatarUrl: user.avatarUrl || getDefaultAvatarForGender(user.gender || 'male').url };
                if (rememberMe) { localStorage.setItem(STORAGE_KEYS.localSessionUser, JSON.stringify(currentUser)); sessionStorage.removeItem(STORAGE_KEYS.sessionUser); }
                else { sessionStorage.setItem(STORAGE_KEYS.sessionUser, JSON.stringify(currentUser)); localStorage.removeItem(STORAGE_KEYS.localSessionUser); }
                errorDiv.classList.add('hidden');
                document.getElementById('login-form').reset();
                showMainApp(); updateUserDisplay(); initializeUserWorkspace();
            } else {
                errorDiv.textContent = 'Invalid username or password';
                errorDiv.classList.remove('hidden');
            }
        });
    }

    // ============================================
    // SIGNUP
    // ============================================
    const signupForm = document.getElementById('signup-form');
    if (signupForm) {
        const genderSelect = document.getElementById('signup-gender');
        const avatarGrid = document.getElementById('avatar-grid');
        if (avatarGrid) { avatarGrid.dataset.selectedAvatarUrl = ''; avatarGrid.dataset.selectedAvatarKey = ''; }
        if (genderSelect) genderSelect.addEventListener('change', renderSignupAvatarOptions);
        signupForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const fullname = document.getElementById('signup-fullname').value.trim();
            const email = document.getElementById('signup-email').value.trim();
            const username = document.getElementById('signup-username').value.trim();
            const gender = document.getElementById('signup-gender').value;
            const password = document.getElementById('signup-password').value;
            const confirmPassword = document.getElementById('signup-confirm-password').value;
            const errorDiv = document.getElementById('signup-error');
            const successDiv = document.getElementById('signup-success');
            const ag = document.getElementById('avatar-grid');
            const selectedAvatarUrl = (ag && ag.dataset.selectedAvatarUrl) ? ag.dataset.selectedAvatarUrl : '';
            const selectedAvatarKey = (ag && ag.dataset.selectedAvatarKey) ? ag.dataset.selectedAvatarKey : '';
            const defaultAvatar = getDefaultAvatarForGender(gender || 'male');
            const avatarUrl = selectedAvatarUrl || defaultAvatar.url;
            const avatarKey = selectedAvatarKey || defaultAvatar.key;
            errorDiv.classList.add('hidden'); successDiv.classList.add('hidden');
            if (!gender) { errorDiv.textContent = 'Please select gender'; errorDiv.classList.remove('hidden'); return; }
            if (password !== confirmPassword) { errorDiv.textContent = 'Passwords do not match'; errorDiv.classList.remove('hidden'); return; }
            if (password.length < 6) { errorDiv.textContent = 'Password must be at least 6 characters'; errorDiv.classList.remove('hidden'); return; }
            if (!fullname) { errorDiv.textContent = 'Full name is required'; errorDiv.classList.remove('hidden'); return; }
            if (!email) { errorDiv.textContent = 'Email is required'; errorDiv.classList.remove('hidden'); return; }
            if (!username) { errorDiv.textContent = 'Username is required'; errorDiv.classList.remove('hidden'); return; }
            let users = [];
            try { users = JSON.parse(localStorage.getItem(STORAGE_KEYS.users) || '[]'); } catch { users = []; }
            if (users.some(u => u.username === username)) { errorDiv.textContent = 'Username already exists'; errorDiv.classList.remove('hidden'); return; }
            if (users.some(u => u.email === email)) { errorDiv.textContent = 'Email already registered'; errorDiv.classList.remove('hidden'); return; }
            users.push({ fullname, email, username, gender: gender || 'male', avatarKey: avatarKey || 'boy', avatarUrl: avatarUrl || getDefaultAvatarForGender('male').url, password, createdAt: new Date().toISOString() });
            localStorage.setItem(STORAGE_KEYS.users, JSON.stringify(users));
            successDiv.textContent = 'Account created successfully! Redirecting to login...';
            successDiv.classList.remove('hidden');
            document.getElementById('signup-form').reset();
            setTimeout(() => { showPage('login'); successDiv.classList.add('hidden'); }, 2000);
        });
    }

    // ============================================
    // LOGOUT
    // ============================================
    window.logout = function logout() {
        if (confirm('Are you sure you want to logout?')) {
            localStorage.removeItem('lawMitraUser'); sessionStorage.removeItem('lawMitraUser');
            currentUser = null; currentConversationId = null;
            showPage('landing'); resetChatAreaToGreeting(); showWelcomeView();
        }
    };

    // ============================================
    // FORCE LIGHT THEME
    // ============================================
    document.body.classList.add('light-theme');

    // ============================================
    // MOBILE SIDEBAR TOGGLE
    // ============================================
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const sidebar = document.querySelector('.sidebar');
    if (mobileMenuBtn && sidebar) {
        mobileMenuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('mobile-open');
            if (sidebarOverlay) sidebarOverlay.style.display = sidebar.classList.contains('mobile-open') ? 'block' : 'none';
        });
    }
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', () => {
            if (sidebar) sidebar.classList.remove('mobile-open');
            sidebarOverlay.style.display = 'none';
        });
    }

    // ============================================
    // CHARACTER COUNTER
    // ============================================
    const mainInput = document.getElementById('main-input');
    const charCounter = document.getElementById('char-counter');
    const MAX_CHARS = 2000;
    if (mainInput && charCounter) {
        mainInput.addEventListener('input', () => {
            const len = mainInput.value.length;
            charCounter.textContent = `${len}/${MAX_CHARS}`;
            charCounter.className = 'char-counter';
            if (len > MAX_CHARS * 0.85) charCounter.classList.add('warn');
            if (len >= MAX_CHARS) charCounter.classList.add('limit');
        });
    }

    // ============================================
    // LEGAL TOPICS PANEL
    // ============================================
    const topicsToggleBtn = document.getElementById('topics-toggle-btn');
    const legalTopicsPanel = document.getElementById('legal-topics-panel');
    if (topicsToggleBtn && legalTopicsPanel) {
        topicsToggleBtn.addEventListener('click', () => legalTopicsPanel.classList.toggle('open'));
    }
    document.querySelectorAll('.topic-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const question = chip.dataset.q;
            if (question) {
                if (legalTopicsPanel) legalTopicsPanel.classList.remove('open');
                toggleView('chat');
                if (!currentConversationId) createNewConversation();
                addMessage(question, true);
                appendToCurrentConversation('user', question);
                sendMessageAndDisplay(question);
            }
        });
    });

    // ============================================
    // EXAMPLE QUESTION BUTTON
    // ============================================
    const askExampleBtn = document.getElementById('ask-example-btn');
    const exampleQuestions = [
        'What are the fundamental rights under the Indian Constitution?',
        'How do I file a complaint under the Consumer Protection Act?',
        'What is the difference between IPC Section 302 and 304?',
        'Explain the process of getting anticipatory bail in India.',
        'What are the rights of a woman under the Domestic Violence Act?',
        'How does the Right to Information Act work?',
        'What is the legal age for marriage in India?',
        'Explain the concept of habeas corpus in Indian law.',
    ];
    if (askExampleBtn) {
        askExampleBtn.addEventListener('click', () => {
            const q = exampleQuestions[Math.floor(Math.random() * exampleQuestions.length)];
            if (mainInput) { mainInput.value = q; mainInput.dispatchEvent(new Event('input')); mainInput.focus(); }
        });
    }

    // ============================================
    // ATTACH ICON → FILE UPLOAD
    // ============================================
    const attachIconBtn = document.getElementById('attach-icon-btn');
    if (attachIconBtn) {
        attachIconBtn.addEventListener('click', () => { const fi = document.getElementById('file-input'); if (fi) fi.click(); });
    }

    // ============================================
    // DOCUMENT STATUS BADGE
    // ============================================
    const docStatusBadge = document.getElementById('doc-status-badge');
    const docBadgeText = document.getElementById('doc-badge-text');

    function showDocBadge(filename) {
        if (docStatusBadge && docBadgeText) {
            docBadgeText.textContent = filename.length > 20 ? filename.slice(0, 18) + '…' : filename;
            docStatusBadge.classList.add('active');
        }
    }
    function hideDocBadge() { if (docStatusBadge) docStatusBadge.classList.remove('active'); }

    if (docStatusBadge) {
        docStatusBadge.addEventListener('click', async () => {
            if (confirm('Remove the uploaded document?')) {
                try { await fetch('/clear_document', { method: 'POST' }); } catch (e) { }
                hideDocBadge();
                addMessage('📄 Document removed. Now in general consultation mode.', false);
            }
        });
    }

    // ============================================
    // VOICE INPUT (Web Speech API)
    // ============================================
    const voiceBtn = document.getElementById('voice-btn');
    let recognition = null;
    let isRecording = false;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-IN';
        recognition.onstart = () => {
            isRecording = true;
            if (voiceBtn) { voiceBtn.classList.add('recording'); voiceBtn.title = 'Recording... click to stop'; voiceBtn.innerHTML = '<i class="fa-solid fa-stop"></i>'; }
        };
        recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) transcript += event.results[i][0].transcript;
            if (mainInput) { mainInput.value = transcript; mainInput.dispatchEvent(new Event('input')); }
        };
        recognition.onend = () => {
            isRecording = false;
            if (voiceBtn) { voiceBtn.classList.remove('recording'); voiceBtn.title = 'Voice input'; voiceBtn.innerHTML = '<i class="fa-solid fa-microphone"></i>'; }
        };
        recognition.onerror = (event) => {
            isRecording = false;
            if (voiceBtn) { voiceBtn.classList.remove('recording'); voiceBtn.innerHTML = '<i class="fa-solid fa-microphone"></i>'; }
            if (event.error !== 'aborted') console.warn('Speech recognition error:', event.error);
        };
        if (voiceBtn) {
            voiceBtn.addEventListener('click', () => { if (isRecording) recognition.stop(); else recognition.start(); });
        }
    } else {
        if (voiceBtn) voiceBtn.style.display = 'none';
    }

    // ============================================
    // TEXT-TO-SPEECH
    // ============================================
    let currentSpeechUtterance = null;

    function speakText(text, btn) {
        if (!('speechSynthesis' in window)) return;
        if (currentSpeechUtterance) {
            window.speechSynthesis.cancel();
            currentSpeechUtterance = null;
            document.querySelectorAll('.msg-action-btn.speaking').forEach(b => { b.classList.remove('speaking'); b.innerHTML = '<i class="fa-solid fa-volume-high"></i> Listen'; });
            if (btn && btn.dataset.speaking === 'true') { btn.dataset.speaking = 'false'; return; }
        }
        const plainText = text.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
        const utterance = new SpeechSynthesisUtterance(plainText);
        utterance.lang = 'en-IN'; utterance.rate = 0.95; utterance.pitch = 1;
        utterance.onend = () => {
            currentSpeechUtterance = null;
            if (btn) { btn.classList.remove('speaking'); btn.innerHTML = '<i class="fa-solid fa-volume-high"></i> Listen'; btn.dataset.speaking = 'false'; }
        };
        currentSpeechUtterance = utterance;
        if (btn) { btn.classList.add('speaking'); btn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop'; btn.dataset.speaking = 'true'; }
        window.speechSynthesis.speak(utterance);
    }

    // ============================================
    // EXPORT CHAT AS PDF
    // ============================================
    const exportChatBtn = document.getElementById('export-chat-btn');
    if (exportChatBtn) {
        exportChatBtn.addEventListener('click', () => {
            const conversation = getCurrentConversation();
            if (!conversation || !conversation.messages || conversation.messages.length === 0) { alert('No conversation to export yet.'); return; }
            const printWindow = window.open('', '_blank');
            const title = conversation.title || 'LawGuideAI Conversation';
            const date = new Date().toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' });
            let html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${title}</title><style>@page{margin:20mm;size:A4}@media print{body{margin:0}header,footer{display:none}}body{font-family:'Segoe UI',sans-serif;max-width:800px;margin:40px auto;color:#1a1a1a;line-height:1.6}h1{color:#0A2540;border-bottom:2px solid #C59D5F;padding-bottom:10px}.meta{color:#666;font-size:.85rem;margin-bottom:30px}.msg{margin-bottom:20px;padding:14px 18px;border-radius:8px}.user-msg{background:#e8f0fe;border-left:4px solid #2563eb}.bot-msg{background:#f8f9fa;border-left:4px solid #C59D5F}.role{font-weight:700;font-size:.8rem;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}.user-msg .role{color:#2563eb}.bot-msg .role{color:#b45309}.disclaimer{margin-top:40px;padding:12px;background:#fff3cd;border-radius:6px;font-size:.8rem;color:#856404}</style></head><body>`;
            html += `<h1>⚖️ LawGuideAI — ${title}</h1><div class="meta">Exported on ${date} • ${conversation.messages.length} messages</div>`;
            conversation.messages.forEach(msg => {
                const isUser = msg.role === 'user';
                const content = msg.content.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
                html += `<div class="msg ${isUser ? 'user-msg' : 'bot-msg'}"><div class="role">${isUser ? '👤 You' : '🤖 LawGuideAI'}</div><div>${content}</div></div>`;
            });
            html += `<div class="disclaimer">⚠️ LawGuideAI provides general legal information only. For specific legal advice, please consult a qualified attorney.</div></body></html>`;
            printWindow.document.write(html);
            printWindow.document.close();
            printWindow.focus();
            setTimeout(() => printWindow.print(), 500);
        });
    }

    // ============================================
    // ADD MESSAGE (with Copy + TTS buttons)
    // ============================================
    function addMessage(message, isUser = false) {
        const chatScrollArea = document.querySelector('.chat-scroll-area');
        const messageRow = document.createElement('div');
        messageRow.className = `message-row ${isUser ? 'user' : 'bot'}`;
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        if (isUser) {
            avatar.className += ' user-avatar';
            const avatarUrl = currentUser ? getAvatarForUser(currentUser) : 'https://i.pravatar.cc/150?img=68';
            avatar.innerHTML = `<img src="${avatarUrl}" alt="User">`;
        } else {
            avatar.className += ' bot-avatar';
            avatar.innerHTML = '<img src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" alt="AI">';
        }
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content-wrapper';
        const messageBubble = document.createElement('div');
        messageBubble.className = `message-bubble ${isUser ? 'user-bubble' : 'bot-bubble'}`;
        let isJson = false, jsonData = null;
        if (!isUser) {
            try {
                const jsonMatch = message.match(/\{[\s\S]*\}/);
                if (jsonMatch) {
                    const p = JSON.parse(jsonMatch[0]);
                    if (p.topic && Array.isArray(p.points)) { jsonData = p; isJson = true; }
                }
            } catch (e) { }
        }
        if (isJson && jsonData) {
            let html = `<div class="json-topic">${jsonData.topic}</div>`;
            jsonData.points.forEach((point, i) => {
                html += `<div class="legal-point"><div class="point-header"><span class="point-number">${i + 1}</span><span class="point-title-text">${point.title}</span></div><div class="point-desc">${point.description}</div></div>`;
            });
            messageBubble.innerHTML = html;
        } else {
            if (typeof marked !== 'undefined') messageBubble.innerHTML = marked.parse(message);
            else messageBubble.innerHTML = message.replace(/\n/g, '<br>');
        }
        messageContent.appendChild(messageBubble);
        if (!isUser) {
            addMessageActions(messageBubble, messageContent, message);
        }
        messageRow.appendChild(avatar);
        messageRow.appendChild(messageContent);
        chatScrollArea.appendChild(messageRow);
        chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
    }

    // Helper to add Copy and Listen buttons to bot messages
    function addMessageActions(messageBubble, messageContent, rawText) {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';
        
        const copyBtn = document.createElement('button');
        copyBtn.className = 'msg-action-btn';
        copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
        copyBtn.title = 'Copy to clipboard';
        copyBtn.addEventListener('click', async () => {
            const plainText = messageBubble.innerText || messageBubble.textContent;
            try {
                await navigator.clipboard.writeText(plainText);
                copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                setTimeout(() => { copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy'; }, 2000);
            } catch (e) {
                copyBtn.innerHTML = '<i class="fa-solid fa-xmark"></i> Failed';
                setTimeout(() => { copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy'; }, 2000);
            }
        });
        
        const listenBtn = document.createElement('button');
        listenBtn.className = 'msg-action-btn';
        listenBtn.innerHTML = '<i class="fa-solid fa-volume-high"></i> Listen';
        listenBtn.title = 'Read aloud';
        listenBtn.dataset.speaking = 'false';
        
        if ('speechSynthesis' in window) {
            listenBtn.addEventListener('click', () => speakText(rawText, listenBtn));
        } else {
            listenBtn.style.display = 'none';
        }
        
        actionsDiv.appendChild(copyBtn);
        actionsDiv.appendChild(listenBtn);
        messageContent.appendChild(actionsDiv);
    }

    // Streaming text response reader + real-time UI updates
    async function sendMessageAndDisplay(message) {
        const chatScrollArea = document.querySelector('.chat-scroll-area');
        
        // Add animated typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message-row bot';
        typingDiv.innerHTML = `<div class="avatar bot-avatar"><img src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" alt="AI"></div><div class="message-content-wrapper"><div class="message-bubble bot-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div></div>`;
        chatScrollArea.appendChild(typingDiv);
        chatScrollArea.scrollTop = chatScrollArea.scrollHeight;

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            if (typingDiv.parentNode) typingDiv.parentNode.removeChild(typingDiv);

            if (response.status === 429) {
                const data = await response.json();
                addMessage(data.response || '⏱️ Rate limit exceeded. Please wait a moment and try again.', false);
                return;
            }

            if (!response.ok) {
                addMessage('⚠️ An error occurred. Please try again.', false);
                return;
            }

            // Create streaming message bubble container
            const messageRow = document.createElement('div');
            messageRow.className = 'message-row bot';
            
            const avatar = document.createElement('div');
            avatar.className = 'avatar bot-avatar';
            avatar.innerHTML = '<img src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" alt="AI">';
            
            const messageContent = document.createElement('div');
            messageContent.className = 'message-content-wrapper';
            
            const messageBubble = document.createElement('div');
            messageBubble.className = 'message-bubble bot-bubble';
            
            messageContent.appendChild(messageBubble);
            messageRow.appendChild(avatar);
            messageRow.appendChild(messageContent);
            chatScrollArea.appendChild(messageRow);

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let accumulatedText = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                accumulatedText += chunk;

                // Perform JSON check for structured cards vs markdown
                let isJson = false, jsonData = null;
                try {
                    const jsonMatch = accumulatedText.match(/\{[\s\S]*\}/);
                    if (jsonMatch) {
                        const p = JSON.parse(jsonMatch[0]);
                        if (p.topic && Array.isArray(p.points)) { jsonData = p; isJson = true; }
                    }
                } catch (e) { }

                if (isJson && jsonData) {
                    let html = `<div class="json-topic">${jsonData.topic}</div>`;
                    jsonData.points.forEach((point, i) => {
                        html += `<div class="legal-point"><div class="point-header"><span class="point-number">${i + 1}</span><span class="point-title-text">${point.title}</span></div><div class="point-desc">${point.description}</div></div>`;
                    });
                    messageBubble.innerHTML = html;
                } else {
                    if (typeof marked !== 'undefined') messageBubble.innerHTML = marked.parse(accumulatedText);
                    else messageBubble.innerHTML = accumulatedText.replace(/\n/g, '<br>');
                }
                chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
            }

            // Save conversation state and attach action buttons
            appendToCurrentConversation('bot', accumulatedText);
            addMessageActions(messageBubble, messageContent, accumulatedText);

        } catch (error) {
            console.error('Error:', error);
            if (typingDiv.parentNode) typingDiv.parentNode.removeChild(typingDiv);
            addMessage('⚠️ Network error. Please check your connection and try again.', false);
        }
    }

    // ============================================
    // INIT GREETING TEMPLATE
    // ============================================
    const chatScrollArea = document.querySelector('.chat-scroll-area');
    if (chatScrollArea && chatScrollArea.firstElementChild) {
        greetingTemplateHTML = chatScrollArea.firstElementChild.outerHTML;
    }

    // Check auth on load
    checkAuth();

    // ============================================
    // NEW CHAT BUTTON
    // ============================================
    const newChatBtn = document.querySelector('.new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            startNewConversation();
            fetch('/newchat', { method: 'POST' }).catch(err => console.error(err));
        });
    }

    // ============================================
    // SUGGESTION BUTTONS (welcome screen)
    // ============================================
    document.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const question = btn.textContent.trim();
            toggleView('chat');
            if (!currentConversationId) createNewConversation();
            addMessage(question, true);
            appendToCurrentConversation('user', question);
            await sendMessageAndDisplay(question);
        });
    });

    // ============================================
    // INPUT FIELD & SEND BUTTON
    // ============================================
    const inputField = mainInput || document.querySelector('.input-box input');
    const sendBtn = document.querySelector('.send-btn');

    async function handleSend() {
        if (!inputField) return;
        const message = inputField.value.trim();
        if (!message) return;
        if (!currentConversationId) createNewConversation();
        addMessage(message, true);
        appendToCurrentConversation('user', message);
        inputField.value = '';
        if (charCounter) { charCounter.textContent = `0/${MAX_CHARS}`; charCounter.className = 'char-counter'; }
        await sendMessageAndDisplay(message);
    }

    if (inputField) {
        inputField.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleSend(); });
    }
    if (sendBtn) sendBtn.addEventListener('click', handleSend);

    // ============================================
    // FILE UPLOAD
    // ============================================
    const uploadBtn = document.getElementById('upload-btn');
    const fileInput = document.getElementById('file-input');

    if (uploadBtn && fileInput) {
        uploadBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (file) {
                const formData = new FormData();
                formData.append('file', file);
                try {
                    toggleView('chat');
                    addMessage('📤 Uploading document...', false);
                    const response = await fetch('/upload', { method: 'POST', body: formData });
                    const result = await response.json();
                    const area = document.querySelector('.chat-scroll-area');
                    if (area && area.lastElementChild) area.removeChild(area.lastElementChild);
                    if (response.ok) {
                        const fileName = result.filename || file.name;
                        addMessage(`📄 Document "<strong>${fileName}</strong>" uploaded and processed successfully.<br><br>You can now ask questions about this document.`, false);
                        showDocBadge(fileName);
                    } else {
                        addMessage('❌ Upload failed: ' + result.error, false);
                    }
                } catch (error) {
                    const area = document.querySelector('.chat-scroll-area');
                    if (area && area.lastElementChild && area.lastElementChild.textContent.includes('Uploading')) area.removeChild(area.lastElementChild);
                    addMessage('❌ Upload error: ' + error.message, false);
                }
                e.target.value = '';
            }
        });
    }

    // ============================================
    // GUEST CHAT & LANDING PAGE LOGIC
    // ============================================
    window.startGuestChat = function startGuestChat() {
        if (!currentUser) {
            currentUser = {
                username: 'guest_' + Math.random().toString(36).slice(2, 9),
                fullname: 'Guest User',
                email: 'guest@lawguideai.com',
                gender: 'male',
                avatarKey: 'boy',
                avatarUrl: 'https://randomuser.me/api/portraits/men/1.jpg'
            };
            sessionStorage.setItem(STORAGE_KEYS.sessionUser, JSON.stringify(currentUser));
            updateUserDisplay();
            initializeUserWorkspace();
            startNewConversation();
        }
        showMainApp();
    };

    window.startGuestChatWithQuestion = function startGuestChatWithQuestion(question) {
        if (!currentUser) {
            currentUser = {
                username: 'guest_' + Math.random().toString(36).slice(2, 9),
                fullname: 'Guest User',
                email: 'guest@lawguideai.com',
                gender: 'male',
                avatarKey: 'boy',
                avatarUrl: 'https://randomuser.me/api/portraits/men/1.jpg'
            };
            sessionStorage.setItem(STORAGE_KEYS.sessionUser, JSON.stringify(currentUser));
            showMainApp();
            updateUserDisplay();
            initializeUserWorkspace();
        } else {
            showMainApp();
        }

        startNewConversation();

        setTimeout(async () => {
            addMessage(question, true);
            appendToCurrentConversation('user', question);
            await sendMessageAndDisplay(question);
        }, 200);
    };

}); // end DOMContentLoaded

// ============================================
// PARTICLE ANIMATION
// ============================================
const canvas = document.getElementById('particle-canvas');
const ctx = canvas.getContext('2d');
let particlesArray;

canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

class Particle {
    constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.size = Math.random() * 2 + 0.5;
        this.speedX = (Math.random() * 0.4) - 0.2;
        this.speedY = (Math.random() * 0.4) - 0.2;
        this.color = 'rgba(255, 255, 255, 0.3)';
    }
    update() {
        this.x += this.speedX; this.y += this.speedY;
        if (this.x > canvas.width) this.x = 0;
        if (this.x < 0) this.x = canvas.width;
        if (this.y > canvas.height) this.y = 0;
        if (this.y < 0) this.y = canvas.height;
    }
    draw() {
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
    }
}

function init() {
    particlesArray = [];
    const n = (canvas.width * canvas.height) / 9000;
    for (let i = 0; i < n; i++) particlesArray.push(new Particle());
}

function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particlesArray.forEach(p => { p.update(); p.draw(); });
    requestAnimationFrame(animate);
}

window.addEventListener('resize', () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    init();
});

init();
animate();
