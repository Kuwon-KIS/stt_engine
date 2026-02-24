# Feature 2: Checkboxes for File Selection

**Priority**: MEDIUM  
**Complexity**: MEDIUM  
**Implementation Time**: 3-4 hours  
**Branch**: web-ui

---

## Requirements

Add file selection capabilities to enable:
1. **Checkbox per file** in results table
2. **Select All** checkbox in table header
3. **재수행 (Re-run)** button to reprocess selected files
4. **Export Selected** to export only selected files to CSV

This enables users to:
- Re-run analysis on failed files only
- Export subset of results
- Perform bulk actions on specific files

---

## Design Decisions

### Key Questions

#### Q1: Should re-run create a new job or reuse existing job?
**Options**:
- Option A: Create new job_id for re-run
- Option B: Update existing job, keep same job_id

**Decision**: **Option A** - Create new job
- Preserves history (audit trail)
- Simpler logic (no partial updates)
- Avoids confusion with existing results
- Matches user mental model ("new analysis")

#### Q2: Should we version results for same file?
**Options**:
- Option A: Delete old result, replace with new
- Option B: Keep both with version number

**Decision**: **Option A** - Replace old result
- Simpler for MVP
- Users want "latest" result
- Can add versioning later if needed

#### Q3: How to handle mixed file selections (completed + failed)?
**Decision**: Allow all statuses, warn user before re-run

---

## UI Design

### Checkbox Column in Table

```
┌──────────────────────────────────────────────────────────────────┐
│ 분석 결과 (30건)                                 [선택: 3 / 30]  │
│                                                                   │
│ ┌──┬──────────┬──────────┬──────────┬──────────┬──────────┬───┐│
│ │☑│ 파일명   │ 상태     │ 탐지결과 │ STT 결과 │ 신뢰도   │...││
│ ├──┼──────────┼──────────┼──────────┼──────────┼──────────┼───┤│
│ │☑│ test1.wav│ ✅ 완료  │ 🟢 정상  │ ...      │ 95.3%    │...││
│ │□│ test2.wav│ ⚠️ 의심  │ 🟡 의심  │ ...      │ 45.2%    │...││
│ │☑│ test3.wav│ ❌ 실패  │ -        │ -        │ -        │...││
│ └──┴──────────┴──────────┴──────────┴──────────┴──────────┴───┘│
│                                                                   │
│ [재수행 (3건)] [선택 파일 내보내기] [선택 해제]                  │
└──────────────────────────────────────────────────────────────────┘
```

### Action Buttons

**재수행 (Re-run)** Button:
- Visible when: 1+ files selected
- Action: Create new analysis job for selected files only
- Confirmation: "선택한 3개 파일을 다시 분석하시겠습니까?"
- Result: Redirect to new job_id progress page

**선택 파일 내보내기 (Export Selected)** Button:
- Visible when: 1+ files selected
- Action: Download CSV with selected files only
- Filename: `analysis_results_selected_{timestamp}.csv`

**선택 해제 (Clear Selection)** Button:
- Visible when: 1+ files selected
- Action: Uncheck all checkboxes

---

## Implementation Plan

### Step 1: Frontend HTML Changes

#### A. Add Checkbox Column Header

```html
<thead>
    <tr>
        <th style="width: 40px;">
            <input type="checkbox" 
                   id="selectAllCheckbox" 
                   class="form-check-input" 
                   title="전체 선택">
        </th>
        <th>파일명</th>
        <th>상태</th>
        <th>탐지결과</th>
        <th>STT 결과</th>
        <th>신뢰도</th>
        <th>작업</th>
    </tr>
</thead>
```

#### B. Add Checkbox to Each Row

Modify `renderResults()` function:

```javascript
function renderResults(results) {
    const tbody = document.getElementById('resultsTableBody');
    
    tbody.innerHTML = results.map(result => {
        return `
            <tr data-file-id="${result.filename}">
                <td>
                    <input type="checkbox" 
                           class="file-checkbox form-check-input" 
                           value="${result.filename}"
                           data-status="${result.status}"
                           data-risk="${result.risk_level}">
                </td>
                <td>${result.filename}</td>
                <td>${statusBadge}</td>
                <td>${riskBadge}</td>
                <td class="text-truncate">${result.stt_text || '-'}</td>
                <td>${(result.confidence * 100).toFixed(1)}%</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" 
                            onclick="viewDetail('${result.filename}')">
                        상세보기
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    // Update selection count
    updateSelectionCount();
}
```

#### C. Add Action Buttons Section

```html
<!-- Selection Actions -->
<div class="card-footer bg-light" id="selectionActionsBar" style="display: none;">
    <div class="d-flex justify-content-between align-items-center">
        <div>
            <span class="badge bg-primary" id="selectionCountBadge">0개 선택됨</span>
        </div>
        <div class="btn-group">
            <button class="btn btn-primary" id="rerunSelectedBtn">
                <i class="bi bi-arrow-clockwise"></i> 재수행 (<span id="rerunCount">0</span>건)
            </button>
            <button class="btn btn-success" id="exportSelectedBtn">
                <i class="bi bi-download"></i> 선택 파일 내보내기
            </button>
            <button class="btn btn-outline-secondary" id="clearSelectionBtn">
                <i class="bi bi-x-circle"></i> 선택 해제
            </button>
        </div>
    </div>
</div>
```

### Step 2: JavaScript Selection Logic

```javascript
// ============================================================================
// Selection State
// ============================================================================
let selectedFiles = new Set();

// ============================================================================
// Selection Functions
// ============================================================================

/**
 * Update selection count and toggle action bar
 */
function updateSelectionCount() {
    const checkboxes = document.querySelectorAll('.file-checkbox');
    selectedFiles.clear();
    
    checkboxes.forEach(cb => {
        if (cb.checked) {
            selectedFiles.add(cb.value);
        }
    });
    
    const count = selectedFiles.size;
    
    // Update badges
    document.getElementById('selectionCountBadge').textContent = `${count}개 선택됨`;
    document.getElementById('rerunCount').textContent = count;
    
    // Show/hide action bar
    const actionBar = document.getElementById('selectionActionsBar');
    if (count > 0) {
        actionBar.style.display = 'block';
    } else {
        actionBar.style.display = 'none';
    }
    
    // Update Select All checkbox state
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (count === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (count === checkboxes.length) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true; // Partial selection
    }
}

/**
 * Handle Select All checkbox
 */
function handleSelectAll(checked) {
    const checkboxes = document.querySelectorAll('.file-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = checked;
    });
    updateSelectionCount();
}

/**
 * Handle individual checkbox change
 */
function handleCheckboxChange() {
    updateSelectionCount();
}

/**
 * Clear all selections
 */
function clearSelection() {
    const checkboxes = document.querySelectorAll('.file-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = false;
    });
    updateSelectionCount();
}

/**
 * Re-run analysis on selected files
 */
async function rerunSelected() {
    if (selectedFiles.size === 0) {
        alert('파일을 선택해주세요.');
        return;
    }
    
    // Confirmation dialog
    const fileList = Array.from(selectedFiles).slice(0, 5).join('\\n');
    const moreText = selectedFiles.size > 5 ? `\\n... 외 ${selectedFiles.size - 5}개` : '';
    const confirmed = confirm(
        `선택한 ${selectedFiles.size}개 파일을 다시 분석하시겠습니까?\\n\\n${fileList}${moreText}\\n\\n` +
        `새로운 분석 작업이 생성됩니다.`
    );
    
    if (!confirmed) return;
    
    try {
        // Show loading
        const rerunBtn = document.getElementById('rerunSelectedBtn');
        const originalText = rerunBtn.innerHTML;
        rerunBtn.disabled = true;
        rerunBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>재분석 중...';
        
        // Call backend API
        const response = await fetch('/api/analysis/rerun', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                original_job_id: currentJobId,
                file_ids: Array.from(selectedFiles)
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Redirect to new job
            alert(`재분석 작업이 시작되었습니다. (Job ID: ${data.job_id})`);
            window.location.href = `/analysis/${data.job_id}`;
        } else {
            throw new Error(data.message || '재분석 시작 실패');
        }
    } catch (error) {
        alert('재분석 시작 중 오류가 발생했습니다: ' + error.message);
        console.error('Rerun error:', error);
        
        // Restore button
        rerunBtn.disabled = false;
        rerunBtn.innerHTML = originalText;
    }
}

/**
 * Export selected files to CSV
 */
function exportSelected() {
    if (selectedFiles.size === 0) {
        alert('내보낼 파일을 선택해주세요.');
        return;
    }
    
    // Filter results to selected only
    const selectedResults = currentResults.filter(r => selectedFiles.has(r.filename));
    
    // Generate CSV
    const csv = generateCSV(selectedResults);
    
    // Download
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const filename = `analysis_results_selected_${timestamp}.csv`;
    downloadCSV(csv, filename);
    
    // Show success message
    showToast(`${selectedFiles.size}개 파일을 내보냈습니다.`, 'success');
}

// ============================================================================
// Event Listeners
// ============================================================================

// Select All checkbox
document.getElementById('selectAllCheckbox').addEventListener('change', (e) => {
    handleSelectAll(e.target.checked);
});

// Delegate individual checkbox events (for dynamically created checkboxes)
document.getElementById('resultsTableBody').addEventListener('change', (e) => {
    if (e.target.classList.contains('file-checkbox')) {
        handleCheckboxChange();
    }
});

// Action buttons
document.getElementById('rerunSelectedBtn').addEventListener('click', rerunSelected);
document.getElementById('exportSelectedBtn').addEventListener('click', exportSelected);
document.getElementById('clearSelectionBtn').addEventListener('click', clearSelection);
```

### Step 3: Backend API Endpoint

**File**: `app/routes/analysis.py` (or create new route)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.services.analysis_service import AnalysisService
from app.dependencies import get_current_user

router = APIRouter()

class RerunRequest(BaseModel):
    """재분석 요청"""
    original_job_id: str
    file_ids: List[str]  # Files to re-run

class RerunResponse(BaseModel):
    """재분석 응답"""
    success: bool
    job_id: str
    message: str

@router.post("/api/analysis/rerun", response_model=RerunResponse)
async def rerun_analysis(
    request: RerunRequest,
    emp_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    선택한 파일만 재분석
    
    Args:
        request: 재분석 요청 (job_id, file_ids)
        emp_id: 사번 (from session)
        db: Database session
    
    Returns:
        새로운 job_id와 성공 여부
    """
    try:
        # 1. Validate original job exists and belongs to user
        original_job = db.query(AnalysisJob).filter(
            AnalysisJob.job_id == request.original_job_id,
            AnalysisJob.emp_id == emp_id
        ).first()
        
        if not original_job:
            raise HTTPException(status_code=404, detail="원본 작업을 찾을 수 없습니다")
        
        # 2. Validate file_ids exist in original job
        invalid_files = set(request.file_ids) - set(original_job.file_ids)
        if invalid_files:
            raise HTTPException(
                status_code=400, 
                detail=f"유효하지 않은 파일: {', '.join(invalid_files)}"
            )
        
        # 3. Create new job with selected files only
        new_job_id = str(uuid.uuid4())
        files_hash = AnalysisService.calculate_files_hash(request.file_ids)
        
        new_job = AnalysisJob(
            job_id=new_job_id,
            emp_id=emp_id,
            folder_path=original_job.folder_path,
            file_ids=request.file_ids,
            files_hash=files_hash,
            status="pending",
            options=original_job.options,  # Reuse same options
            created_at=datetime.utcnow()
        )
        
        db.add(new_job)
        db.commit()
        
        # 4. Start processing in background
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            AnalysisService.process_analysis_sync,
            job_id=new_job_id,
            emp_id=emp_id,
            folder_path=original_job.folder_path,
            files=request.file_ids,
            include_classification=original_job.options.get("include_classification", True),
            include_validation=original_job.options.get("include_validation", True)
        )
        
        logger.info(f"[rerun_analysis] Created new job {new_job_id} from {request.original_job_id}")
        
        return RerunResponse(
            success=True,
            job_id=new_job_id,
            message=f"{len(request.file_ids)}개 파일 재분석 시작"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[rerun_analysis] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"재분석 시작 실패: {str(e)}")
```

### Step 4: Register Route

**File**: `main.py`

```python
# Add to imports
from app.routes import analysis_routes

# Add to app
app.include_router(analysis_routes.router)
```

---

## Database Changes

**Required**: NONE ✅

The feature reuses existing tables:
- New `AnalysisJob` row for re-run
- New `AnalysisResult` rows for selected files
- New `AnalysisProgress` rows for tracking

No schema changes needed.

---

## Testing Plan

### Test Case 1: Select All
1. View analysis results (10 files)
2. Click Select All checkbox
3. ✅ Verify all 10 checkboxes checked
4. ✅ Verify "10개 선택됨" badge shown
5. ✅ Verify action bar visible

### Test Case 2: Partial Selection
1. Check 3 out of 10 files
2. ✅ Verify Select All shows indeterminate state (-)
3. ✅ Verify "3개 선택됨" badge
4. Uncheck 1 file
5. ✅ Verify count updates to "2개 선택됨"

### Test Case 3: Clear Selection
1. Select 5 files
2. Click "선택 해제" button
3. ✅ Verify all checkboxes unchecked
4. ✅ Verify action bar hidden

### Test Case 4: Re-run Selected
1. Select 3 files (mix of completed and failed)
2. Click "재수행 (3건)" button
3. ✅ Verify confirmation dialog shows file list
4. Confirm re-run
5. ✅ Verify API called with correct file_ids
6. ✅ Verify redirect to new job_id page
7. ✅ Verify only 3 files being processed

### Test Case 5: Export Selected
1. Select 5 files
2. Click "선택 파일 내보내기" button
3. ✅ Verify CSV downloaded
4. ✅ Verify CSV contains only 5 files
5. ✅ Verify filename includes timestamp

### Test Case 6: Re-run with Filters
1. Apply filter (status="failed")
2. Select visible files only
3. Re-run selected
4. ✅ Verify only selected files re-run (not all failed)

### Test Case 7: Error Handling
1. Select files from deleted job
2. Try to re-run
3. ✅ Verify 404 error handled gracefully
4. ✅ Verify error message shown to user

---

## File Modifications

### Files to Modify
1. `templates/analysis.html`
   - Add checkbox column (~50 lines)
   - Add action bar (~30 lines)
   - Add JavaScript logic (~200 lines)

2. `app/routes/analysis.py` (or create `app/routes/analysis_routes.py`)
   - Add `/api/analysis/rerun` endpoint (~80 lines)

3. `main.py`
   - Register new router (2 lines)

### Total Lines: ~360 lines

---

## Edge Cases & Considerations

### Edge Case 1: Empty Selection
**Behavior**: Disable action buttons or show alert
**Implementation**: Check `selectedFiles.size === 0` before actions

### Edge Case 2: Re-run In-Progress Job
**Behavior**: Allow (user might want parallel runs)
**Note**: Creates separate job, no conflict

### Edge Case 3: Re-run Same Files Twice
**Behavior**: Allow (creates separate jobs)
**Note**: Each creates new job_id, preserves history

### Edge Case 4: Large Selection (50+ files)
**Behavior**: Warn user, show truncated list in confirmation
**Implementation**: Show first 10 files + "... 외 N개"

### Edge Case 5: Selection Persistence Across Filters
**Behavior**: Preserve selection even if filtered out
**Implementation**: Use `selectedFiles` Set, independent of display

### Edge Case 6: Selection After Page Reload
**Behavior**: Clear selection (not persistent)
**Note**: Could add localStorage persistence in Phase 2

---

## Security Considerations

### Authorization Check
✅ Backend validates `emp_id` matches original job owner
```python
if original_job.emp_id != emp_id:
    raise HTTPException(status_code=403, detail="권한 없음")
```

### Input Validation
✅ Validate file_ids exist in original job
```python
invalid_files = set(request.file_ids) - set(original_job.file_ids)
if invalid_files:
    raise HTTPException(400, "유효하지 않은 파일")
```

### Rate Limiting
⚠️ Consider adding rate limit for re-run API (prevent abuse)
```python
# Future enhancement
@limiter.limit("10/minute")
async def rerun_analysis(...):
```

---

## Future Enhancements

### Phase 2 Features
1. **Smart Selection**: Quick buttons
   - "Select All Failed" - Auto-select status='failed'
   - "Select All High Risk" - Auto-select risk='danger'
   - "Invert Selection" - Toggle all checkboxes

2. **Bulk Delete**: Delete selected files (with confirmation)

3. **Persistent Selection**: Save in localStorage across page reloads

4. **Batch Actions Menu**: Dropdown with more actions
   - Re-classify selected
   - Re-validate selected
   - Archive selected

### Phase 3 Features
1. **Drag-and-Drop Reordering**: Change file order before re-run
2. **Partial Re-run Options**: Choose which steps to re-run (STT only, classification only, etc.)
3. **Compare Results**: Show before/after comparison for re-run files

---

## Implementation Estimate

**Total Time**: 3-4 hours

Breakdown:
- Frontend HTML/UI: 45 minutes
- JavaScript selection logic: 60 minutes
- Backend API endpoint: 45 minutes
- Testing: 60 minutes
- Edge case handling: 30 minutes

**Complexity**: ⭐⭐⭐☆☆ (Medium)  
**Risk**: ⭐⭐☆☆☆ (Low-Medium - new backend endpoint)  
**Value**: ⭐⭐⭐⭐☆ (High - enables powerful workflows)

---

## Rollback Plan

If issues arise:

### Frontend Rollback
1. Remove checkbox column from table
2. Remove action bar section
3. Remove selection JavaScript functions
4. No database impact

### Backend Rollback
1. Comment out `/api/analysis/rerun` route
2. Remove route registration from main.py
3. No database impact (new jobs already created are fine)

---

## Conclusion

Feature 2 adds powerful bulk operation capabilities that significantly improve user workflow efficiency. The implementation is moderately complex but well-scoped, with clear separation between frontend (selection UI) and backend (re-run logic).

**Key Benefits**:
- ✅ Re-run failed files without reprocessing entire batch
- ✅ Export subsets of results for reporting
- ✅ Foundation for future bulk operations
- ✅ Clean separation of concerns (UI vs API)

**Recommendation**: ✅ IMPLEMENT after Feature 1

**Implementation Order**:
1. Implement Recommendation 2 ✅ (Done)
2. Implement Recommendation 4 ✅ (Done)
3. Implement Feature 1 (Filters) ← NEXT
4. Implement Feature 2 (Checkboxes) ← AFTER Feature 1
