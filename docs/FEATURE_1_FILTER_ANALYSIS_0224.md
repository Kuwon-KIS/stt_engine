# Feature 1: Filter by 분석상태 & 판매탐지

**Priority**: HIGH  
**Complexity**: LOW  
**Implementation Time**: 1-2 hours  
**Branch**: web-ui

---

## Requirements

Allow users to filter analysis results by:
1. **분석상태 (Analysis Status)**: pending, processing, completed, failed
2. **판매탐지 (Risk Detection)**: safe, warning, danger

This improves usability when dealing with large result sets (50+ files).

---

## Design Decisions

### Option A: Client-Side Filtering (✅ RECOMMENDED)
**Pros**:
- No backend changes required
- Instant filtering (no API calls)
- Works with existing data structure
- Simple to implement

**Cons**:
- Filters only visible results (pagination issue)
- Not suitable for 1000+ results

### Option B: Server-Side Filtering
**Pros**:
- Handles large datasets
- Can paginate filtered results
- More scalable

**Cons**:
- Requires backend API changes
- Slower (network latency)
- More complex implementation

**Decision**: Use **Option A (Client-Side)** for now. The typical use case involves 10-50 files per analysis job, which is perfect for client-side filtering. We can migrate to server-side if needed later.

---

## UI Design

### Filter Location
Place filters above the results table, below the job info:

```
┌─────────────────────────────────────────────────────────┐
│ 분석 작업 정보                                           │
│ 폴더: [uploads/test_batch]  상태: [완료]               │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ 필터                                                     │
│ 분석상태: [전체 ▾] [대기중] [처리중] [완료] [실패]      │
│ 판매탐지: [전체 ▾] [정상] [의심] [부당권유 발견]        │
│                              [필터 초기화] 버튼          │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ 분석 결과 (Filtered: 15 / 총 30건)                      │
│ ┌──────────┬──────────┬──────────┬──────────┐          │
│ │ 파일명   │ 상태     │ 탐지결과 │ STT 결과 │          │
│ ├──────────┼──────────┼──────────┼──────────┤          │
│ │ test1.wav│ ✅ 완료  │ 🟢 정상  │ ...      │          │
│ │ test2.wav│ ⚠️ 의심  │ 🟡 의심  │ ...      │          │
│ │ test3.wav│ ❌ 위험  │ 🔴 위험  │ ...      │          │
│ └──────────┴──────────┴──────────┴──────────┘          │
└─────────────────────────────────────────────────────────┘
```

### Filter Options

#### 분석상태 (Status)
- **전체** (all) - Default
- **대기중** (pending) - status='pending'
- **처리중** (processing) - status='processing'
- **완료** (completed) - status='completed'
- **실패** (failed) - status='failed'

#### 판매탐지 (Risk Level)
- **전체** (all) - Default
- **정상** (safe) - risk_level='safe'
- **의심** (warning) - risk_level='warning'
- **부당권유 발견** (danger) - risk_level='danger'

---

## Implementation Plan

### Step 1: Frontend HTML (analysis.html)

**Location**: After job info, before results table

```html
<!-- Filter Section -->
<div class="card mb-3" id="filterSection" style="display: none;">
    <div class="card-header">
        <h6 class="mb-0">
            <i class="bi bi-funnel"></i> 필터
        </h6>
    </div>
    <div class="card-body">
        <div class="row g-3">
            <!-- Status Filter -->
            <div class="col-md-6">
                <label class="form-label fw-bold">분석상태</label>
                <div class="btn-group w-100" role="group" id="statusFilterButtons">
                    <input type="radio" class="btn-check" name="statusFilter" id="status_all" value="all" checked>
                    <label class="btn btn-outline-primary" for="status_all">전체</label>
                    
                    <input type="radio" class="btn-check" name="statusFilter" id="status_pending" value="pending">
                    <label class="btn btn-outline-secondary" for="status_pending">대기중</label>
                    
                    <input type="radio" class="btn-check" name="statusFilter" id="status_processing" value="processing">
                    <label class="btn btn-outline-info" for="status_processing">처리중</label>
                    
                    <input type="radio" class="btn-check" name="statusFilter" id="status_completed" value="completed">
                    <label class="btn btn-outline-success" for="status_completed">완료</label>
                    
                    <input type="radio" class="btn-check" name="statusFilter" id="status_failed" value="failed">
                    <label class="btn btn-outline-danger" for="status_failed">실패</label>
                </div>
            </div>
            
            <!-- Risk Level Filter -->
            <div class="col-md-6">
                <label class="form-label fw-bold">판매탐지</label>
                <div class="btn-group w-100" role="group" id="riskFilterButtons">
                    <input type="radio" class="btn-check" name="riskFilter" id="risk_all" value="all" checked>
                    <label class="btn btn-outline-primary" for="risk_all">전체</label>
                    
                    <input type="radio" class="btn-check" name="riskFilter" id="risk_safe" value="safe">
                    <label class="btn btn-outline-success" for="risk_safe">🟢 정상</label>
                    
                    <input type="radio" class="btn-check" name="riskFilter" id="risk_warning" value="warning">
                    <label class="btn btn-outline-warning" for="risk_warning">🟡 의심</label>
                    
                    <input type="radio" class="btn-check" name="riskFilter" id="risk_danger" value="danger">
                    <label class="btn btn-outline-danger" for="risk_danger">🔴 위험</label>
                </div>
            </div>
        </div>
        
        <div class="mt-3 text-end">
            <button class="btn btn-sm btn-outline-secondary" id="resetFiltersBtn">
                <i class="bi bi-arrow-clockwise"></i> 필터 초기화
            </button>
        </div>
        
        <!-- Filter Stats -->
        <div class="mt-2 text-muted small" id="filterStats">
            표시: <span id="filteredCount">0</span> / 전체: <span id="totalCount">0</span>건
        </div>
    </div>
</div>
```

### Step 2: JavaScript Filter Logic

**Location**: In `<script>` section of analysis.html

```javascript
// ============================================================================
// Filter State
// ============================================================================
let currentResults = []; // Store all results
let currentFilters = {
    status: 'all',
    risk: 'all'
};

// ============================================================================
// Filter Functions
// ============================================================================

/**
 * Apply filters to results
 */
function applyFilters() {
    const filtered = currentResults.filter(result => {
        // Status filter
        if (currentFilters.status !== 'all' && result.status !== currentFilters.status) {
            return false;
        }
        
        // Risk filter
        if (currentFilters.risk !== 'all' && result.risk_level !== currentFilters.risk) {
            return false;
        }
        
        return true;
    });
    
    // Update display
    renderResults(filtered);
    updateFilterStats(filtered.length, currentResults.length);
}

/**
 * Update filter statistics
 */
function updateFilterStats(filteredCount, totalCount) {
    document.getElementById('filteredCount').textContent = filteredCount;
    document.getElementById('totalCount').textContent = totalCount;
}

/**
 * Reset all filters
 */
function resetFilters() {
    currentFilters = {
        status: 'all',
        risk: 'all'
    };
    
    // Reset radio buttons
    document.getElementById('status_all').checked = true;
    document.getElementById('risk_all').checked = true;
    
    // Reapply (shows all)
    applyFilters();
}

/**
 * Render results to table
 */
function renderResults(results) {
    const tbody = document.getElementById('resultsTableBody');
    if (!tbody) return;
    
    if (results.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted py-4">
                    <i class="bi bi-inbox"></i><br>
                    필터 조건에 맞는 결과가 없습니다
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = results.map(result => {
        // Status badge
        let statusBadge = '';
        switch (result.status) {
            case 'pending':
                statusBadge = '<span class="badge bg-secondary">대기중</span>';
                break;
            case 'processing':
                statusBadge = '<span class="badge bg-info">처리중</span>';
                break;
            case 'completed':
                statusBadge = '<span class="badge bg-success">완료</span>';
                break;
            case 'failed':
                statusBadge = '<span class="badge bg-danger">실패</span>';
                break;
        }
        
        // Risk badge
        let riskBadge = '';
        switch (result.risk_level) {
            case 'safe':
                riskBadge = '<span class="badge bg-success">🟢 정상</span>';
                break;
            case 'warning':
                riskBadge = '<span class="badge bg-warning text-dark">🟡 의심</span>';
                break;
            case 'danger':
                riskBadge = '<span class="badge bg-danger">🔴 위험</span>';
                break;
        }
        
        return `
            <tr>
                <td>${result.filename}</td>
                <td>${statusBadge}</td>
                <td>${riskBadge}</td>
                <td class="text-truncate" style="max-width: 300px;">
                    ${result.stt_text || '<span class="text-muted">-</span>'}
                </td>
                <td>${(result.confidence * 100).toFixed(1)}%</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewDetail('${result.filename}')">
                        상세보기
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// ============================================================================
// Event Listeners
// ============================================================================

// Status filter change
document.querySelectorAll('input[name="statusFilter"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        currentFilters.status = e.target.value;
        applyFilters();
    });
});

// Risk filter change
document.querySelectorAll('input[name="riskFilter"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        currentFilters.risk = e.target.value;
        applyFilters();
    });
});

// Reset button
document.getElementById('resetFiltersBtn').addEventListener('click', resetFilters);

// ============================================================================
// Update existing updateProgress function
// ============================================================================

// Modify existing updateProgress to store results globally
function updateProgress(jobId) {
    fetch(`/api/analysis/progress/${jobId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const progress = data.progress;
                
                // Store results globally for filtering
                currentResults = progress.results || [];
                
                // Show filter section once we have results
                if (currentResults.length > 0) {
                    document.getElementById('filterSection').style.display = 'block';
                }
                
                // Apply current filters
                applyFilters();
                
                // ... rest of existing code ...
            }
        })
        .catch(error => {
            console.error('Error fetching progress:', error);
        });
}
```

### Step 3: CSS Styling

```css
/* Filter Section Styles */
#filterSection {
    border-left: 4px solid #0d6efd;
}

#filterSection .btn-group {
    flex-wrap: wrap;
}

#filterSection .btn-check:checked + label {
    font-weight: bold;
}

#filterStats {
    font-size: 0.875rem;
}

/* Results table responsive */
#resultsTableBody .text-truncate {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
```

---

## Testing Plan

### Test Case 1: Status Filtering
1. Upload 5 files for analysis
2. While processing, click "처리중" filter
3. ✅ Verify only processing files shown
4. Wait for completion
5. Click "완료" filter
6. ✅ Verify only completed files shown

### Test Case 2: Risk Filtering
1. Complete analysis with mixed risk levels
2. Click "정상" (safe) filter
3. ✅ Verify only safe files shown
4. Click "위험" (danger) filter
5. ✅ Verify only danger files shown

### Test Case 3: Combined Filtering
1. Set status="완료" AND risk="위험"
2. ✅ Verify only completed AND dangerous files shown
3. Click "필터 초기화"
4. ✅ Verify all files shown again

### Test Case 4: Empty Results
1. Set filter combination with no matches (e.g., status="failed")
2. ✅ Verify empty state message shown
3. Reset filters
4. ✅ Verify results reappear

### Test Case 5: Real-Time Updates
1. Start analysis
2. Set filter to "처리중"
3. ✅ Verify processing file appears
4. Wait for completion
5. ✅ Verify file disappears from filtered view (now completed)

---

## Backend Changes

**Required**: NONE ✅

The existing API already returns:
- `status`: 'pending', 'processing', 'completed', 'failed'
- `risk_level`: 'safe', 'warning', 'danger'

All filtering logic is client-side.

---

## File Modifications

### Files to Modify
1. `templates/analysis.html` - Add filter UI and JavaScript
   - Lines to add: ~200 (HTML + JS)
   - Location: After job info section

### Files to Create
- None (pure frontend feature)

---

## Rollback Plan

If issues arise:
1. Remove filter section HTML (`div#filterSection`)
2. Remove filter JavaScript functions
3. Restore original `renderResults()` function

No database or backend changes to rollback.

---

## Future Enhancements

### Phase 2 Improvements
1. **Persistent Filters**: Save filter state in localStorage
2. **URL Parameters**: Support `/analysis?status=failed&risk=danger`
3. **Quick Filters**: One-click "Show Only Problems" button
4. **Search**: Add text search for filenames
5. **Sort**: Add column sorting (filename, confidence, etc.)

### Phase 3 Improvements
1. **Server-Side Filtering**: For large datasets (100+ files)
2. **Export Filtered**: CSV export of filtered results only
3. **Filter Presets**: Save/load filter combinations
4. **Advanced Filters**: Date range, confidence range sliders

---

## Implementation Estimate

**Total Time**: 1-2 hours

Breakdown:
- HTML UI: 30 minutes
- JavaScript logic: 45 minutes
- CSS styling: 15 minutes
- Testing: 30 minutes

**Complexity**: ⭐⭐☆☆☆ (Low)  
**Risk**: ⭐☆☆☆☆ (Very Low - client-side only)  
**Value**: ⭐⭐⭐⭐⭐ (High - major UX improvement)

---

## Conclusion

Feature 1 is a high-value, low-risk enhancement that significantly improves usability for users analyzing multiple files. The client-side implementation is simple, fast, and requires no backend changes.

**Recommendation**: ✅ IMPLEMENT IMMEDIATELY after Recommendations 2 & 4

**Next Steps**:
1. Add HTML filter section
2. Implement JavaScript filter logic
3. Test with real data
4. Deploy to web-ui branch
