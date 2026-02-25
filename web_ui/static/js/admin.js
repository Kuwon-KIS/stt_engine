/**
 * Admin Panel JavaScript
 * Handles admin authentication, user management, and quota updates
 */

// Show admin modal
function showAdminModal() {
    const modal = document.getElementById('adminModal');
    const authSection = document.getElementById('adminAuthSection');
    const panelSection = document.getElementById('adminPanelSection');
    
    // Reset to auth screen
    authSection.style.display = 'block';
    panelSection.style.display = 'none';
    document.getElementById('adminPassword').value = '';
    document.getElementById('adminAuthError').style.display = 'none';
    
    modal.style.display = 'flex';
}

// Close admin modal
function closeAdminModal() {
    const modal = document.getElementById('adminModal');
    modal.style.display = 'none';
    
    // Clear admin session
    fetch('/api/admin/logout', {
        method: 'POST',
        credentials: 'include'
    }).catch(err => console.error('Logout error:', err));
}

// Authenticate admin
async function authenticateAdmin() {
    const password = document.getElementById('adminPassword').value;
    const errorDiv = document.getElementById('adminAuthError');
    
    if (!password) {
        errorDiv.textContent = '비밀번호를 입력해주세요';
        errorDiv.style.display = 'block';
        return;
    }
    
    try {
        const response = await fetch('/api/admin/auth', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Show admin panel
            document.getElementById('adminAuthSection').style.display = 'none';
            document.getElementById('adminPanelSection').style.display = 'block';
            
            // Load users
            await loadUsers();
        } else {
            errorDiv.textContent = data.error || '인증 실패';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Admin auth error:', error);
        errorDiv.textContent = '네트워크 오류가 발생했습니다';
        errorDiv.style.display = 'block';
    }
}

// Show tab
function showTab(tabName) {
    // Update tab buttons
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Show/hide tab content
    document.getElementById('userListTab').style.display = 
        tabName === 'userList' ? 'block' : 'none';
    document.getElementById('createUserTab').style.display = 
        tabName === 'createUser' ? 'block' : 'none';
}

// Load users
async function loadUsers() {
    const tbody = document.getElementById('userTableBody');
    
    try {
        const response = await fetch('/api/admin/users', {
            credentials: 'include'
        });
        
        if (response.status === 403) {
            // Session expired
            alert('관리자 세션이 만료되었습니다. 다시 로그인해주세요.');
            closeAdminModal();
            return;
        }
        
        const data = await response.json();
        
        if (data.success && data.users) {
            if (data.users.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" style="padding: 40px; text-align: center; color: #9ca3af;">
                            등록된 사용자가 없습니다
                        </td>
                    </tr>
                `;
                return;
            }
            
            tbody.innerHTML = data.users.map(user => {
                // 사용량 표시 로직 개선
                let usageDisplay;
                const usedBytes = user.storage_used;
                const usedMB = usedBytes / (1024 * 1024);
                const usedGB = usedBytes / (1024 * 1024 * 1024);
                
                if (usedBytes === 0) {
                    usageDisplay = '0 MB';
                } else if (usedGB >= 1) {
                    usageDisplay = `${usedGB.toFixed(2)} GB`;
                } else {
                    usageDisplay = `${usedMB.toFixed(2)} MB`;
                }
                
                return `
                    <tr>
                        <td style="padding: 10px;">${user.emp_id}</td>
                        <td style="padding: 10px;">${user.name}</td>
                        <td style="padding: 10px;">${user.dept || '-'}</td>
                        <td style="padding: 10px; text-align: right;">${usageDisplay}</td>
                        <td style="padding: 10px; text-align: right;">
                            <input 
                                type="number" 
                                id="quota-${user.emp_id}"
                                class="quota-input"
                                value="${user.storage_quota_gb}" 
                                min="1" 
                                max="1000"
                                step="1"
                                data-original="${user.storage_quota_gb}"
                                oninput="handleQuotaChange()"
                                style="width: 80px; padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 4px;"
                            />
                        </td>
                        <td style="padding: 10px; text-align: center;">
                            ${user.is_admin ? '✅' : '-'}
                        </td>
                    </tr>
                `;
            }).join('');
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="padding: 40px; text-align: center; color: #ef4444;">
                        사용자 목록을 불러올 수 없습니다
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Load users error:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="padding: 40px; text-align: center; color: #ef4444;">
                    네트워크 오류가 발생했습니다
                </td>
            </tr>
        `;
    }
}

// Handle quota input change - check all inputs for changes
function handleQuotaChange() {
    const saveAllBtn = document.getElementById('saveAllBtn');
    if (!saveAllBtn) return;
    
    const inputs = document.querySelectorAll('.quota-input');
    let hasChanges = false;
    
    inputs.forEach(input => {
        const original = input.getAttribute('data-original');
        const current = input.value;
        if (original !== current && current.trim() !== '') {
            hasChanges = true;
        }
    });
    
    // Enable/disable save all button based on changes
    if (hasChanges) {
        saveAllBtn.disabled = false;
        saveAllBtn.style.opacity = '1';
        saveAllBtn.style.pointerEvents = 'auto';
    } else {
        saveAllBtn.disabled = true;
        saveAllBtn.style.opacity = '0.5';
        saveAllBtn.style.pointerEvents = 'none';
    }
}

// Save all changed quotas
async function saveAllChanges() {
    const inputs = document.querySelectorAll('.quota-input');
    const changes = [];
    
    // Collect all changes
    inputs.forEach(input => {
        const empId = input.id.replace('quota-', '');
        const original = parseFloat(input.getAttribute('data-original'));
        const current = parseFloat(input.value);
        
        if (original !== current && !isNaN(current)) {
            // Validation
            if (current <= 0 || current > 1000) {
                alert(`${empId} 사용자의 할당량은 1GB ~ 1000GB 사이여야 합니다`);
                input.value = original;
                return;
            }
            changes.push({ empId, quota: current, input });
        }
    });
    
    if (changes.length === 0) {
        showToast('변경된 내용이 없습니다', 'info');
        return;
    }
    
    // Show saving state
    const saveAllBtn = document.getElementById('saveAllBtn');
    const originalText = saveAllBtn.textContent;
    saveAllBtn.textContent = '💾 저장중...';
    saveAllBtn.disabled = true;
    saveAllBtn.style.opacity = '0.7';
    
    // Disable all inputs during save
    inputs.forEach(input => input.disabled = true);
    
    let successCount = 0;
    let failCount = 0;
    
    // Save all changes
    for (const change of changes) {
        try {
            const response = await fetch(`/api/admin/users/${change.empId}/quota`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({ quota_gb: change.quota })
            });
            
            if (response.status === 403) {
                alert('관리자 세션이 만료되었습니다. 다시 로그인해주세요.');
                closeAdminModal();
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Update original value
                change.input.setAttribute('data-original', change.quota);
                successCount++;
            } else {
                // Revert to original
                change.input.value = change.input.getAttribute('data-original');
                failCount++;
            }
        } catch (error) {
            console.error('Update quota error:', error);
            change.input.value = change.input.getAttribute('data-original');
            failCount++;
        }
    }
    
    // Re-enable inputs
    inputs.forEach(input => input.disabled = false);
    
    // Show results
    if (failCount === 0) {
        saveAllBtn.textContent = '✓ 완료';
        saveAllBtn.style.background = '#10b981';
        showToast(`${successCount}개 사용자의 할당량이 변경되었습니다`, 'success');
    } else {
        saveAllBtn.textContent = originalText;
        showToast(`${successCount}개 성공, ${failCount}개 실패`, 'info');
    }
    
    // Reset button after delay
    setTimeout(() => {
        saveAllBtn.textContent = originalText;
        saveAllBtn.style.background = '#667eea';
        handleQuotaChange();
    }, 2000);
}

// Show toast notification
function showToast(message, type = 'info') {
    // Remove existing toast
    const existingToast = document.getElementById('admin-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Create toast
    const toast = document.createElement('div');
    toast.id = 'admin-toast';
    toast.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : '#667eea'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 100001;
        font-size: 14px;
        animation: slideInUp 0.3s ease-out;
    `;
    toast.textContent = message;
    
    // Add animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInUp {
            from {
                transform: translateY(100%);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
    
    document.body.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideInUp 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Create user
async function createUser(event) {
    event.preventDefault();
    
    const empId = document.getElementById('newEmpId').value.trim();
    const name = document.getElementById('newName').value.trim();
    const dept = document.getElementById('newDept').value.trim();
    
    const errorDiv = document.getElementById('createUserError');
    const successDiv = document.getElementById('createUserSuccess');
    
    // Hide previous messages
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';
    
    // Validate
    if (!/^\d{6}$/.test(empId)) {
        errorDiv.textContent = '사번은 6자리 숫자여야 합니다';
        errorDiv.style.display = 'block';
        return;
    }
    
    if (!name || !dept) {
        errorDiv.textContent = '모든 필드를 입력해주세요';
        errorDiv.style.display = 'block';
        return;
    }
    
    try {
        const response = await fetch('/api/admin/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                emp_id: empId,
                name: name,
                dept: dept
            })
        });
        
        if (response.status === 403) {
            alert('관리자 세션이 만료되었습니다. 다시 로그인해주세요.');
            closeAdminModal();
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            successDiv.textContent = data.message || '사용자가 생성되었습니다';
            successDiv.style.display = 'block';
            
            // Clear form
            document.getElementById('createUserForm').reset();
            
            // Reload user list
            await loadUsers();
            
            // Auto-hide success message
            setTimeout(() => {
                successDiv.style.display = 'none';
            }, 3000);
        } else {
            errorDiv.textContent = data.error || '사용자 생성 실패';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Create user error:', error);
        errorDiv.textContent = '네트워크 오류가 발생했습니다';
        errorDiv.style.display = 'block';
    }
}

// Close modal on outside click
window.onclick = function(event) {
    const modal = document.getElementById('adminModal');
    if (event.target === modal) {
        closeAdminModal();
    }
}

// Handle Enter key in password field
document.addEventListener('DOMContentLoaded', () => {
    const passwordInput = document.getElementById('adminPassword');
    if (passwordInput) {
        passwordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                authenticateAdmin();
            }
        });
    }
});
