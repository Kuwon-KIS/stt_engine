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
            
            tbody.innerHTML = data.users.map(user => `
                <tr>
                    <td style="padding: 10px;">${user.emp_id}</td>
                    <td style="padding: 10px;">${user.name}</td>
                    <td style="padding: 10px;">${user.dept || '-'}</td>
                    <td style="padding: 10px; text-align: right;">${user.storage_used_gb.toFixed(2)}</td>
                    <td style="padding: 10px; text-align: right;">
                        <input 
                            type="number" 
                            value="${user.storage_quota_gb}" 
                            min="1" 
                            max="1000"
                            step="1"
                            onchange="updateQuota('${user.emp_id}', this.value)"
                        />
                    </td>
                    <td style="padding: 10px; text-align: center;">
                        ${user.is_admin ? '✅' : '-'}
                    </td>
                </tr>
            `).join('');
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

// Update user quota
async function updateQuota(empId, quotaGb) {
    const quota = parseFloat(quotaGb);
    
    if (isNaN(quota) || quota <= 0 || quota > 1000) {
        alert('할당량은 1GB ~ 1000GB 사이여야 합니다');
        await loadUsers(); // Reload to reset input
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${empId}/quota`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ quota_gb: quota })
        });
        
        if (response.status === 403) {
            alert('관리자 세션이 만료되었습니다. 다시 로그인해주세요.');
            closeAdminModal();
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Show success feedback (subtle)
            const input = event.target;
            const originalBg = input.style.backgroundColor;
            input.style.backgroundColor = '#d1fae5';
            setTimeout(() => {
                input.style.backgroundColor = originalBg;
            }, 500);
        } else {
            alert(data.error || '할당량 변경 실패');
            await loadUsers(); // Reload to reset input
        }
    } catch (error) {
        console.error('Update quota error:', error);
        alert('네트워크 오류가 발생했습니다');
        await loadUsers(); // Reload to reset input
    }
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
