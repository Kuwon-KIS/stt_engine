/**
 * 공용 유틸리티 함수 (Phase 1)
 * 세션 관리, API 호출, 알림 표시 등
 */

// === 1. 세션 관리 ===

/**
 * 현재 세션 정보 확인
 * 미인증 시 로그인 페이지로 리다이렉트
 * @returns {Promise<Object|null>} 세션 정보 또는 null
 */
async function checkSession() {
    try {
        const response = await fetch('/api/auth/session');
        if (response.ok) {
            return await response.json();
        } else if (response.status === 401) {
            // 로그인 필요
            window.location.href = '/';
            return null;
        }
    } catch (error) {
        console.error('Session check failed:', error);
        return null;
    }
}

/**
 * 로그아웃
 * @returns {Promise<void>}
 */
async function logout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
        window.location.href = '/';
    } catch (error) {
        console.error('Logout failed:', error);
        showNotification('로그아웃 실패', 'error');
    }
}

// === 2. API 호출 헬퍼 ===

/**
 * API 호출 래퍼 함수
 * @param {string} endpoint - API 엔드포인트
 * @param {string} method - HTTP 메서드 (GET, POST, etc)
 * @param {Object} body - 요청 본문 (method가 GET이 아닐 경우)
 * @returns {Promise<Object|null>} 응답 데이터 또는 null
 */
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include'  // 쿠키 포함 (세션 유지)
    };

    if (body && method !== 'GET') {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(endpoint, options);
        const data = await response.json();

        if (!response.ok) {
            const errorMsg = data.detail || data.message || 'API 호출 실패';
            showNotification(errorMsg, 'error');
            
            // 401 에러 (미인증)
            if (response.status === 401) {
                window.location.href = '/';
            }
            
            return null;
        }

        return data;
    } catch (error) {
        console.error('API call error:', error);
        showNotification('네트워크 오류: ' + error.message, 'error');
        return null;
    }
}

// === 3. 알림 표시 ===

/**
 * 화면 상단에 알림 표시
 * @param {string} message - 알림 메시지
 * @param {string} type - 알림 타입 ('info', 'success', 'warning', 'error')
 * @param {number} duration - 자동 사라질 시간 (ms, 기본: 5000)
 */
function showNotification(message, type = 'info', duration = 5000) {
    // 기존 알림 찾기
    let notifContainer = document.getElementById('notification-container');
    
    // 없으면 생성
    if (!notifContainer) {
        notifContainer = document.createElement('div');
        notifContainer.id = 'notification-container';
        notifContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
        `;
        document.body.appendChild(notifContainer);
    }

    // 알림 엘리먼트 생성
    const notif = document.createElement('div');
    notif.className = `notification notification-${type}`;
    notif.textContent = message;
    notif.style.cssText = `
        padding: 15px 20px;
        border-radius: 6px;
        margin-bottom: 10px;
        font-size: 14px;
        animation: slideIn 0.3s ease-out;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    `;

    // 타입별 배경색
    const colors = {
        info: '#e3f2fd',
        success: '#e8f5e9',
        warning: '#fff3e0',
        error: '#ffebee'
    };
    const textColors = {
        info: '#1976d2',
        success: '#388e3c',
        warning: '#f57c00',
        error: '#d32f2f'
    };

    notif.style.backgroundColor = colors[type] || colors.info;
    notif.style.color = textColors[type] || textColors.info;
    notif.style.border = `1px solid ${textColors[type] || textColors.info}`;

    notifContainer.appendChild(notif);

    // 자동 제거
    if (duration > 0) {
        setTimeout(() => {
            notif.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notif.remove(), 300);
        }, duration);
    }
}

// === 4. 포맷 유틸리티 ===

/**
 * 파일 크기를 읽기 좋은 형식으로 변환
 * @param {number} bytes - 바이트 단위 크기
 * @returns {string} 포맷된 크기 (예: "2.5 MB")
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * 날짜를 한국 형식으로 변환
 * @param {string|Date} dateStr - 날짜 문자열 또는 Date 객체
 * @returns {string} 포맷된 날짜 (예: "2026. 02. 20. 14:30")
 */
function formatDate(dateStr) {
    const date = new Date(dateStr);
    
    return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * 날짜와 시간을 포맷팅 (formatDate의 별칭)
 * @param {string|Date} dateStr - 날짜 문자열 또는 Date 객체
 * @returns {string} 포맷된 날짜 (예: "2026. 02. 20. 14:30:45")
 */
function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    
    if (isNaN(date.getTime())) return '-';
    
    return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * 시간을 읽기 좋은 형식으로 변환
 * @param {number} seconds - 초 단위 시간
 * @returns {string} 포맷된 시간 (예: "1h 23m 45s")
 */
function formatDuration(seconds) {
    if (seconds < 60) {
        return Math.round(seconds) + 's';
    }
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.round(seconds % 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    }
    
    return `${minutes}m ${secs}s`;
}

/**
 * 백분율을 진행 바로 표시
 * @param {number} percent - 백분율 (0-100)
 * @param {boolean} showText - 텍스트 표시 여부
 * @returns {string} HTML 진행 바
 */
function createProgressBar(percent, showText = true) {
    const clampedPercent = Math.min(Math.max(percent, 0), 100);
    const text = showText ? `${clampedPercent}%` : '';
    
    return `
        <div style="
            width: 100%;
            height: 24px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        ">
            <div style="
                width: ${clampedPercent}%;
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                transition: width 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                <span style="
                    color: white;
                    font-size: 12px;
                    font-weight: 600;
                ">${text}</span>
            </div>
        </div>
    `;
}

// === 5. DOM 유틸리티 ===

/**
 * 로딩 스피너 표시
 * @returns {HTMLElement}
 */
function createLoadingSpinner() {
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    spinner.style.cssText = `
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid #f3f3f3;
        border-top: 3px solid #667eea;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    `;
    
    // CSS 애니메이션 정의 (아직 없으면)
    if (!document.getElementById('spinner-animation')) {
        const style = document.createElement('style');
        style.id = 'spinner-animation';
        style.textContent = `
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }
    
    return spinner;
}

/**
 * 페이지 로드 시 세션 자동 확인
 * (문서 로드 완료 후 실행)
 */
document.addEventListener('DOMContentLoaded', async () => {
    // 이미 checkSession이 호출되어 있으면 스킵
    if (window.skipAutoSessionCheck) {
        return;
    }
    
    // 특정 페이지 (예: login.html)는 세션 확인 스킵
    const currentPage = window.location.pathname;
    if (currentPage.includes('/login') || currentPage.includes('/index.html')) {
        return;
    }
    
    // 세션 확인
    const session = await checkSession();
    if (!session) {
        console.warn('Session check failed, user may not be authenticated');
    }
});

// === CSS 스타일 추가 ===
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
    
    .notification {
        word-wrap: break-word;
        white-space: normal;
    }
`;
document.head.appendChild(style);
