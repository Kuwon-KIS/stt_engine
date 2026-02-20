/**
 * STT Web UI - 메인 JavaScript
 */

// ============================================================================
// 글로벌 변수
// ============================================================================

let selectedFile = null;
let currentFileId = null;
let currentBatchId = null;
let batchProgressInterval = null;

// API 기본 URL
const API_BASE = "/api";

// ============================================================================
// 유틸리티 함수
// ============================================================================

/**
 * API 호출 함수 (ENHANCED)
 */
async function apiCall(endpoint, method = "GET", data = null) {
    const options = {
        method,
        headers: {
            "Content-Type": "application/json"
        }
    };

    if (data && method !== "GET") {
        options.body = JSON.stringify(data);
    }

    console.log(`[API] ${method} ${endpoint}`, data || "");

    try {
        const response = await fetch(API_BASE + endpoint, options);
        
        // 응답 상태 로깅
        console.log(`[API Response] ${endpoint}: ${response.status} ${response.statusText}`);
        
        let json;
        try {
            json = await response.json();
        } catch (parseError) {
            console.error(`[API Parse Error] ${endpoint}:`, parseError);
            throw new Error(`응답 파싱 실패: ${response.statusText}`);
        }

        if (!response.ok) {
            // 에러 응답 처리 (ENHANCED)
            const errorMessage = json.error || json.detail || json.error_code || "요청 실패";
            const errorCode = json.error_code || "UNKNOWN";
            console.error(`[API Error] ${endpoint} (${errorCode}):`, errorMessage);
            throw new Error(`[${errorCode}] ${errorMessage}`);
        }

        console.log(`[API Success] ${endpoint}:`, json);
        return json;
        
    } catch (error) {
        console.error(`[API Call Failed] ${endpoint}:`, error.message);
        // UI 알림 없음 - 호출처에서 처리
        throw error;
    }
}

/**
 * 파일 크기 포맷
 */
function formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

/**
 * 시간 포맷
 */
function formatTime(seconds) {
    if (!seconds) return "-";
    if (seconds < 60) return Math.round(seconds) + "초";
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(0);
    return `${mins}분 ${secs}초`;
}

/**
 * 알림 표시
 */
function showNotification(message, type = "info") {
    console.log(`[${type.toUpperCase()}] ${message}`);
    // 실제 UI 알림은 필요시 구현
}

/**
 * UI 섹션 표시/숨김
 */
function showSection(sectionId) {
    document.querySelectorAll(".section").forEach(s => {
        s.style.display = s.id === sectionId ? "block" : "none";
    });
}

// ============================================================================
// 파일 업로드 로직
// ============================================================================

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const browseBtn = document.querySelector(".browse-btn");
const fileInfo = document.getElementById("file-info");
const transcribeBtn = document.getElementById("transcribe-btn");
const languageSelect = document.getElementById("language-select");
const backendSelect = document.getElementById("backend-select");
const streamingCheckbox = document.getElementById("streaming-checkbox");
const setGlobalBackendCheckbox = document.getElementById("set-global-backend-checkbox");
const currentApiBackend = document.getElementById("current-api-backend");

// ============================================================================
// 파일 업로드 이벤트 핸들러 설정 (DOMContentLoaded 후)
// ============================================================================

/**
 * 모든 파일 업로드 이벤트 리스너 등록
 */
function initializeFileUploadHandlers() {
    console.log("[Init] 파일 업로드 핸들러 초기화 시작");
    
    if (!dropZone) {
        console.error("[Error] drop-zone 요소를 찾을 수 없습니다");
        return;
    }
    
    if (!fileInput) {
        console.error("[Error] file-input 요소를 찾을 수 없습니다");
        return;
    }
    
    if (!browseBtn) {
        console.error("[Error] browse-btn 요소를 찾을 수 없습니다");
        return;
    }

    // 드래그 & 드롭 이벤트
    // dragover: 파일을 드래그하여 영역 위에 올렸을 때
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add("active");
        console.log("[DragDrop] dragover 이벤트 발생");
    });

    // dragleave: 드래그하던 파일을 영역 밖으로 나갔을 때
    dropZone.addEventListener("dragleave", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("active");
        console.log("[DragDrop] dragleave 이벤트 발생");
    });

    // dragend: 드래그 작업이 완료되었을 때
    dropZone.addEventListener("dragend", (e) => {
        e.preventDefault();
        dropZone.classList.remove("active");
        console.log("[DragDrop] dragend 이벤트 발생");
    });

    // drop: 파일을 드롭했을 때
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("active");
        
        console.log("[DragDrop] drop 이벤트 발생, 파일 수:", e.dataTransfer.files.length);
        
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            console.log("[DragDrop] 드롭된 파일:", file.name, file.type, file.size);
            handleFileSelect(file);
        }
    });

    // 드롭 존 클릭 이벤트 (파일 입력 트리거)
    dropZone.addEventListener("click", (e) => {
        console.log("[Click] drop-zone 클릭 감지");
        fileInput.click();
    });

    // 파일 입력 요소의 change 이벤트
    fileInput.addEventListener("change", (e) => {
        console.log("[FileInput] change 이벤트 발생, 파일 수:", e.target.files.length);
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            console.log("[FileInput] 선택된 파일:", file.name, file.type, file.size);
            handleFileSelect(file);
        }
    });

    // "클릭하여 선택" 버튼 이벤트
    browseBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        console.log("[Browse] 버튼 클릭");
        fileInput.click();
    });
    
    console.log("[Init] 파일 업로드 핸들러 초기화 완료");
}

/**
 * 파일 선택 처리
 */
function handleFileSelect(file) {
    selectedFile = file;
    fileInfo.textContent = `선택됨: ${file.name} (${formatFileSize(file.size)})`;
    dropZone.classList.add("has-file");
    transcribeBtn.disabled = false;
    showNotification(`파일 선택: ${file.name}`, "info");
}

/**
 * 파일 업로드
 */
async function uploadFile() {
    if (!selectedFile) {
        showNotification("녹취 파일을 선택해주세요", "error");
        return;
    }

    try {
        const formData = new FormData();
        formData.append("file", selectedFile);

        showLoading("녹취 파일 업로드 중...");

        const response = await fetch(API_BASE + "/upload/", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "업로드 실패");
        }

        currentFileId = result.file_id;
        showNotification(`업로드 완료: ${result.file_id}`, "info");
        return result;

    } catch (error) {
        showNotification(`업로드 실패: ${error.message}`, "error");
        hideLoading();
        throw error;
    }
}

/**
 * 글로벌 백엔드 정보 조회
 */
async function fetchGlobalBackendInfo() {
    try {
        const response = await fetch(API_BASE + "/backend/current");
        if (!response.ok) {
            throw new Error("백엔드 정보 조회 실패");
        }
        const data = await response.json();
        const backendName = data.current_backend || "unknown";
        currentApiBackend.textContent = `API: ${backendName}`;
        return backendName;
    } catch (error) {
        console.error("백엔드 정보 조회 실패:", error);
        currentApiBackend.textContent = "API: 오류";
    }
}

/**
 * 글로벌 백엔드 변경
 */
async function setGlobalBackend(backend) {
    try {
        if (!backend) {
            showNotification("변경할 백엔드를 선택해주세요", "error");
            return false;
        }

        showNotification(`API 백엔드를 ${backend}로 변경 중...`, "info");

        const response = await fetch(API_BASE + "/backend/reload", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ backend: backend })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || "백엔드 변경 실패");
        }

        showNotification(`API 백엔드가 ${backend}로 변경되었습니다 ✅`, "info");
        await fetchGlobalBackendInfo();
        return true;
    } catch (error) {
        console.error("백엔드 변경 실패:", error);
        showNotification(`백엔드 변경 실패: ${error.message}`, "error");
        return false;
    }
}

/**
 * STT 처리
 */
async function transcribeFile() {
    try {
        // 파일 업로드
        const uploadResult = await uploadFile();
        if (!uploadResult) return;

        // 글로벌 백엔드 설정 체크
        if (setGlobalBackendCheckbox.checked && backendSelect.value) {
            const success = await setGlobalBackend(backendSelect.value);
            if (!success) {
                showNotification("백엔드 설정 실패로 인해 처리를 중단했습니다", "error");
                hideLoading();
                return;
            }
        }

        showLoading("녹취 음성 분석 중...");

        // STT 처리
        const language = languageSelect.value;
        const backend = backendSelect.value || undefined;
        const isStream = streamingCheckbox.checked;
        
        // 처리 옵션 (NEW)
        const privacyRemoval = document.getElementById("privacy-removal-checkbox")?.checked || false;
        const classification = document.getElementById("classification-checkbox")?.checked || false;
        const aiAgent = document.getElementById("ai-agent-checkbox")?.checked || false;
        
        console.log("[Transcribe] 처리 옵션:", { privacy_removal: privacyRemoval, classification, ai_agent: aiAgent });
        
        const result = await apiCall("/transcribe/", "POST", {
            file_id: uploadResult.file_id,
            language: language,
            backend: backend,
            is_stream: isStream,
            privacy_removal: privacyRemoval,      // NEW
            classification: classification,        // NEW
            ai_agent: aiAgent                     // NEW
        });

        hideLoading();

        // 결과 표시
        displayResult(result);
        showNotification("녹취 분석 완료", "info");

    } catch (error) {
        hideLoading();
        showNotification(`분석 실패: ${error.message}`, "error");
        console.error("[Transcribe Error]", error);
    }
}

/**
 * 결과 표시
 */
function displayResult(result) {
    const resultText = result.text || "";
    document.getElementById("result-text").textContent = resultText || "(텍스트 없음)";
    document.getElementById("metric-duration").textContent = formatTime(result.duration_sec);
    document.getElementById("metric-time").textContent = formatTime(result.processing_time_sec);
    
    // word_count: API에서 받은 값이 없으면 텍스트 길이로 계산
    const wordCount = result.word_count !== undefined && result.word_count !== null 
        ? result.word_count 
        : resultText.length;
    document.getElementById("metric-word-count").textContent = wordCount.toString();
    
    document.getElementById("metric-backend").textContent = result.backend || "-";
    
    // 처리 단계 표시 (NEW)
    if (result.processing_steps) {
        console.log("[Result] Processing Steps:", result.processing_steps);
        displayProcessingSteps(result.processing_steps);
    }
    
    // Privacy Removal 결과 표시 (NEW)
    if (result.privacy_removal) {
        console.log("[Result] Privacy Removal:", result.privacy_removal);
        displayPrivacyResults(result.privacy_removal);
    }
    
    // Classification 결과 표시 (NEW)
    if (result.classification) {
        console.log("[Result] Classification:", result.classification);
        displayClassificationResults(result.classification);
    }
    
    // 성능 메트릭 표시
    if (result.performance) {
        const perf = result.performance;
        const perfSection = document.getElementById("performance-metrics");
        if (perfSection) {
            perfSection.style.display = "block";
            
            // 성능 메트릭 HTML 생성
            const perfHtml = `
                <div class="perf-row">
                    <div class="perf-item">
                        <label>CPU 평균</label>
                        <value>${perf.cpu_percent_avg.toFixed(1)}%</value>
                    </div>
                    <div class="perf-item">
                        <label>CPU 최대</label>
                        <value>${perf.cpu_percent_max.toFixed(1)}%</value>
                    </div>
                </div>
                <div class="perf-row">
                    <div class="perf-item">
                        <label>RAM 평균</label>
                        <value>${perf.ram_mb_avg.toFixed(0)} MB</value>
                    </div>
                    <div class="perf-item">
                        <label>RAM 피크</label>
                        <value>${perf.ram_mb_peak.toFixed(0)} MB</value>
                    </div>
                </div>
                <div class="perf-row">
                    <div class="perf-item">
                        <label>GPU VRAM</label>
                        <value>${perf.gpu_vram_mb_current.toFixed(0)} MB</value>
                    </div>
                    <div class="perf-item">
                        <label>GPU 사용률</label>
                        <value>${perf.gpu_percent.toFixed(1)}%</value>
                    </div>
                </div>
            `;
            
            document.getElementById("perf-content").innerHTML = perfHtml;
        }
    } else {
        const perfSection = document.getElementById("performance-metrics");
        if (perfSection) {
            perfSection.style.display = "none";
        }
    }

    // 섹션 전환
    document.getElementById("upload-section").style.display = "none";
    document.getElementById("result-section").style.display = "block";
    
    // Privacy Removal 섹션 표시 ✨
    showPrivacyRemovalOptions();
    
    // 스크롤
    document.getElementById("result-section").scrollIntoView({ behavior: "smooth" });
}

/**
 * 처리 단계 표시 (NEW)
 */
function displayProcessingSteps(steps) {
    const section = document.getElementById("processing-steps-section");
    const content = document.getElementById("processing-steps-content");
    
    if (!section || !content) return;
    
    const stepsHtml = `
        <div style="padding: 8px; background: ${steps.stt ? '#d4edda' : '#f8d7da'}; border-radius: 4px;">
            <span>${steps.stt ? '✅' : '❌'} STT 변환</span>
        </div>
        <div style="padding: 8px; background: ${steps.privacy_removal ? '#d4edda' : '#f8d7da'}; border-radius: 4px;">
            <span>${steps.privacy_removal ? '✅' : '❌'} 개인정보 제거</span>
        </div>
        <div style="padding: 8px; background: ${steps.classification ? '#d4edda' : '#f8d7da'}; border-radius: 4px;">
            <span>${steps.classification ? '✅' : '❌'} 통화 분류</span>
        </div>
        <div style="padding: 8px; background: ${steps.ai_agent ? '#d4edda' : '#f8d7da'}; border-radius: 4px;">
            <span>${steps.ai_agent ? '✅' : '❌'} AI Agent 처리</span>
        </div>
    `;
    
    content.innerHTML = stepsHtml;
    section.style.display = "block";
}

/**
 * Privacy Removal 결과 표시 (NEW)
 */
function displayPrivacyResults(privacy) {
    const section = document.getElementById("privacy-result-section");
    if (!section) return;
    
    const hasPrivacy = privacy.exist ? "예 (개인정보 감지됨)" : "아니오";
    const reason = privacy.reason || "확인되지 않음";
    const processedText = privacy.processed_text || "-";
    
    document.getElementById("privacy-exist").textContent = hasPrivacy;
    document.getElementById("privacy-reason").textContent = reason;
    document.getElementById("privacy-text").textContent = processedText;
    
    section.style.display = "block";
    console.log("[Privacy Results] 표시됨");
}

/**
 * Classification 결과 표시 (NEW)
 */
function displayClassificationResults(classification) {
    const section = document.getElementById("classification-result-section");
    if (!section) return;
    
    document.getElementById("class-code").textContent = classification.code || "-";
    document.getElementById("class-category").textContent = classification.category || "-";
    document.getElementById("class-confidence").textContent = 
        classification.confidence ? `${(classification.confidence * 100).toFixed(1)}%` : "-";
    document.getElementById("class-reason").textContent = classification.reason || "-";
    
    section.style.display = "block";
    console.log("[Classification Results] 표시됨");
}

// 결과 액션
document.getElementById("copy-btn")?.addEventListener("click", () => {
    const text = document.getElementById("result-text").textContent;
    navigator.clipboard.writeText(text).then(() => {
        showNotification("복사되었습니다", "info");
    });
});

document.getElementById("download-txt-btn")?.addEventListener("click", () => {
    const text = document.getElementById("result-text").textContent;
    const element = document.createElement("a");
    element.setAttribute("href", "data:text/plain;charset=utf-8," + encodeURIComponent(text));
    element.setAttribute("download", "result.txt");
    element.style.display = "none";
    document.body.appendChild(element);
    console.log("[다운로드] TXT 파일 다운로드 시작");
    element.click();
    document.body.removeChild(element);
    showNotification("TXT 파일이 다운로드되었습니다", "info");
});

document.getElementById("download-json-btn")?.addEventListener("click", async () => {
    try {
        console.log(`[다운로드] JSON 파일 다운로드 요청: ${currentFileId}`);
        const data = await apiCall(`/results/${currentFileId}/export?format=json`);
        const element = document.createElement("a");
        element.setAttribute("href", "data:application/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2)));
        element.setAttribute("download", "result.json");
        element.style.display = "none";
        document.body.appendChild(element);
        console.log("[다운로드] JSON 파일 다운로드 시작");
        element.click();
        document.body.removeChild(element);
        showNotification("JSON 파일이 다운로드되었습니다", "info");
    } catch (error) {
        console.error("[다운로드실패]", error);
        showNotification(`다운로드 실패: ${error.message}`, "error");
    }
});

document.getElementById("reset-btn")?.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    fileInfo.textContent = "";
    dropZone.classList.remove("has-file");
    transcribeBtn.disabled = true;
    languageSelect.value = "ko";
    backendSelect.value = "";
    streamingCheckbox.checked = false;
    setGlobalBackendCheckbox.checked = false;
    document.getElementById("result-section").style.display = "none";
    document.getElementById("upload-section").style.display = "block";
    resetPrivacyRemovalSection();  // Privacy Removal 초기화 ✨
});

// 버튼 이벤트
transcribeBtn.addEventListener("click", transcribeFile);

// ============================================================================
// 배치 처리 로직
// ============================================================================

const loadFilesBtn = document.getElementById("load-files-btn");
const startBatchBtn = document.getElementById("start-batch-btn");
const batchExtensionInput = document.getElementById("batch-extension");
const batchLanguageSelect = document.getElementById("batch-language");
const batchParallelInput = document.getElementById("batch-parallel");

let batchFiles = [];

/**
 * 배치 파일 로드
 */
loadFilesBtn?.addEventListener("click", async () => {
    try {
        loadFilesBtn.disabled = true;
        loadFilesBtn.textContent = "로드 중...";

        const extension = batchExtensionInput.value || ".wav";
        const result = await apiCall(`/batch/files?extension=${extension}`);

        batchFiles = result.files || [];
        renderBatchTable();

        document.getElementById("batch-table-container").style.display = "block";
        document.getElementById("file-count").textContent = batchFiles.length;
        startBatchBtn.disabled = batchFiles.length === 0;

        showNotification(`${batchFiles.length}개 파일 로드됨`, "info");

    } catch (error) {
        showNotification(`파일 로드 실패: ${error.message}`, "error");
    } finally {
        loadFilesBtn.disabled = false;
        loadFilesBtn.textContent = "파일 목록 로드";
    }
});

/**
 * 배치 테이블 렌더링
 */
function renderBatchTable() {
    const tbody = document.getElementById("batch-table-body");
    tbody.innerHTML = "";

    batchFiles.forEach((file) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${file.name}</td>
            <td>${formatFileSize(file.size_mb * 1024 * 1024)}</td>
            <td><span class="status-pending">${file.status}</span></td>
            <td>-</td>
            <td>-</td>
            <td>-</td>
            <td>-</td>
            <td>-</td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * 배치 처리 시작
 */
startBatchBtn?.addEventListener("click", async () => {
    try {
        startBatchBtn.disabled = true;
        startBatchBtn.textContent = "처리 중...";

        // 처리 옵션 (NEW)
        const privacyRemoval = document.getElementById("privacy-removal-checkbox")?.checked || false;
        const classification = document.getElementById("classification-checkbox")?.checked || false;
        const aiAgent = document.getElementById("ai-agent-checkbox")?.checked || false;
        
        console.log("[배치] 처리 옵션:", { privacy_removal: privacyRemoval, classification, ai_agent });

        const result = await apiCall("/batch/start/", "POST", {
            extension: batchExtensionInput.value || ".wav",
            language: batchLanguageSelect.value,
            parallel_count: parseInt(batchParallelInput.value) || 2,
            privacy_removal: privacyRemoval,     // NEW
            classification: classification,       // NEW
            ai_agent: aiAgent                    // NEW
        });

        currentBatchId = result.batch_id;
        showNotification(`배치 처리 시작: ${result.total_files}개 파일`, "info");

        // 진행 상황 모니터링
        document.getElementById("batch-progress-container").style.display = "block";
        startBatchProgressMonitoring(result.batch_id);

    } catch (error) {
        showNotification(`배치 처리 시작 실패: ${error.message}`, "error");
        console.error("[배치 Error]", error);
    } finally {
        startBatchBtn.disabled = false;
        startBatchBtn.textContent = "배치 처리 시작";
    }
});

/**
 * 배치 진행 상황 모니터링 (ENHANCED)
 */
function startBatchProgressMonitoring(batchId) {
    clearInterval(batchProgressInterval);
    let consoleErrorCount = 0;

    // 즉시 첫 번째 업데이트
    async function updateProgress() {
        try {
            console.log(`[배치진행] 진행상황 조회: ${batchId}`);
            const progress = await apiCall(`/batch/progress/${batchId}/`);

            // UI 업데이트
            const total = progress.total;
            const completed = progress.completed;
            const percentage = (completed / total) * 100;

            const progressFill = document.getElementById("progress-fill");
            progressFill.style.width = percentage + "%";
            progressFill.textContent = Math.round(percentage) + "%";

            document.getElementById("completed-count").textContent = completed;
            document.getElementById("progress-count").textContent = progress.in_progress;
            document.getElementById("failed-count").textContent = progress.failed;
            document.getElementById("remaining-time").textContent = 
                formatTime(progress.estimated_remaining_sec);

            console.log(`[배치진행] 진행률: ${completed}/${total} (${percentage.toFixed(1)}%)`);
            
            // 실패 파일이 있으면 경고 로깅
            if (progress.failed > 0 && progress.files) {
                const failedFiles = progress.files.filter(f => f.status === "failed");
                failedFiles.forEach(f => {
                    console.warn(`[배치실패] ${f.filename}: ${f.error || '알 수 없는 오류'}`);
                });
            }

            // 파일 상태 업데이트
            updateBatchTableStatus(progress.files);

            // 완료 여부 확인
            if (completed + progress.failed === total) {
                clearInterval(batchProgressInterval);
                const successMessage = `배치 처리 완료: ${completed}성공, ${progress.failed}실패`;
                console.log(`[배치완료] ${successMessage}`);
                showNotification(successMessage, "info");
                
                // 배치 완료 후 성능 통계 버튼 표시
                const perfStatsBtn = document.getElementById("batch-perf-stats-btn");
                if (perfStatsBtn) {
                    perfStatsBtn.style.display = "inline-block";
                }
            }
            
            // 에러 카운트 리셋
            consoleErrorCount = 0;

        } catch (error) {
            consoleErrorCount++;
            console.error(`[배치조회실패] 시도 ${consoleErrorCount}: ${error.message}`);
            
            // 연속 3회 실패 시 모니터링 중단
            if (consoleErrorCount >= 3) {
                console.error("[배치조회] 연속 3회 실패로 모니터링 중단");
                clearInterval(batchProgressInterval);
                showNotification("배치 진행상황 조회 실패. 수동으로 새로고침해주세요.", "error");
            }
        }
    }

    // 즉시 첫 번째 호출
    updateProgress();

    // 5초마다 반복 갱신 (빠른 피드백)
    batchProgressInterval = setInterval(updateProgress, 5000);
}

/**
 * 배치 테이블 상태 업데이트
 */
function updateBatchTableStatus(files) {
    const tbody = document.getElementById("batch-table-body");
    const rows = tbody.querySelectorAll("tr");

    console.log(`[Batch] updateBatchTableStatus: ${files.length}개 파일, ${rows.length}개 행`);

    rows.forEach((row, index) => {
        if (files[index]) {
            const file = files[index];
            console.log(`[Batch] 파일 ${index}: ${file.name} - 상태: ${file.status}, 텍스트: ${file.result_text ? 'O' : 'X'}`);
            
            const statusCell = row.children[2];
            const timeCell = row.children[3];
            const durationCell = row.children[4];
            const wordCountCell = row.children[5];
            const resultCell = row.children[6];
            const perfCell = row.children[7];  // 성능 메트릭 셀

            // 상태 업데이트
            statusCell.innerHTML = `<span class="status-${file.status}">${file.status}</span>`;
            
            // 처리 시간
            timeCell.textContent = file.processing_time_sec 
                ? `${file.processing_time_sec.toFixed(1)}초`
                : "-";
            
            // 음성 길이 (분:초 형식)
            durationCell.textContent = file.duration_sec 
                ? formatTime(file.duration_sec)
                : "-";
            
            // 글자 수
            wordCountCell.textContent = (file.word_count !== undefined && file.word_count !== null)
                ? file.word_count.toString()
                : "-";
            
            // 결과 텍스트 업데이트
            if (file.result_text) {
                // 긴 텍스트는 말줄임 처리
                const maxLength = 50;
                const displayText = file.result_text.length > maxLength 
                    ? file.result_text.substring(0, maxLength) + "..." 
                    : file.result_text;
                resultCell.title = file.result_text;  // hover 시 전체 텍스트 보임
                resultCell.textContent = displayText;
                resultCell.style.cursor = "pointer";
                
                // 클릭 시 전체 결과 보기
                resultCell.onclick = () => {
                    showResultModal(file.name, file.result_text, {
                        duration_sec: file.duration_sec,
                        processing_time_sec: file.processing_time_sec,
                        word_count: file.word_count
                    });
                };
            } else if (file.status === "done" && !file.result_text) {
                resultCell.textContent = "(결과 없음)";
            } else if (file.status === "error") {
                resultCell.innerHTML = `<span style="color: red;">${file.error_message || "에러"}</span>`;
            }
            
            // 성능 메트릭 업데이트
            if (file.performance) {
                const perfData = file.performance;
                const perfText = `CPU: ${perfData.cpu_percent_avg?.toFixed(0)}% | RAM: ${perfData.ram_mb_peak?.toFixed(0)}MB`;
                perfCell.textContent = perfText;
                perfCell.title = `CPU: ${perfData.cpu_percent_avg?.toFixed(1)}% (max: ${perfData.cpu_percent_max?.toFixed(1)}%) | RAM: ${perfData.ram_mb_avg?.toFixed(0)}MB avg, ${perfData.ram_mb_peak?.toFixed(0)}MB peak | GPU: ${perfData.gpu_percent?.toFixed(1)}%`;
                perfCell.style.cursor = "pointer";
                perfCell.onclick = () => showBatchPerformanceDetail(file);
            } else {
                perfCell.textContent = "-";
            }
        }
    });
}

/**
 * 결과 모달 표시
 */
function showResultModal(filename, resultText, metadata = {}) {
    const modal = document.createElement("div");
    modal.className = "modal";
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;
    
    const content = document.createElement("div");
    content.style.cssText = `
        background: white;
        border-radius: 8px;
        padding: 20px;
        max-width: 80%;
        max-height: 80%;
        overflow-y: auto;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `;
    
    // 메타데이터 정보 표시
    let metadataHtml = "";
    if (metadata.duration_sec !== undefined) {
        metadataHtml += `<div style="font-size: 12px; color: #666; margin-bottom: 8px;">
            오디오 길이: ${metadata.duration_sec.toFixed(1)}초 | 
            처리 시간: ${metadata.processing_time_sec?.toFixed(1) || '-'}초 |
            글자 수: ${metadata.word_count || '-'}
        </div>`;
    }
    
    content.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px;">
            <h3 style="margin: 0;">${filename}</h3>
            <button onclick="this.parentElement.parentElement.parentElement.remove()" style="background: none; border: none; font-size: 20px; cursor: pointer; color: #999;">×</button>
        </div>
        ${metadataHtml}
        <pre style="background: #f5f5f5; padding: 15px; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; max-height: 400px; overflow-y: auto;">${resultText}</pre>
        <div style="margin-top: 15px; text-align: right;">
            <button onclick="this.parentElement.parentElement.parentElement.remove()" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">닫기</button>
        </div>
    `;
    
    modal.appendChild(content);
    modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.remove();
    });
    
    document.body.appendChild(modal);
}

// ============================================================================
// Privacy Removal 기능
// ============================================================================

const privacyRemovalBtn = document.getElementById("privacy-removal-btn");
const privacyRemovalSection = document.getElementById("privacy-removal-section");
const privacyResultSection = document.getElementById("privacy-result-section");
const privacyProcessing = document.getElementById("privacy-processing");
const privacyPromptType = document.getElementById("privacy-prompt-type");

/**
 * Privacy Removal 처리 시작
 */
async function processPrivacyRemoval() {
    const sttResultTextElem = document.getElementById("result-text");
    const originalText = sttResultTextElem?.textContent || "";
    
    if (!originalText.trim()) {
        showNotification("먼저 STT 결과를 생성해주세요", "warning");
        return;
    }
    
    const promptType = privacyPromptType.value || "privacy_remover_default_v6";
    
    // UI 업데이트
    privacyRemovalBtn.disabled = true;
    privacyProcessing.style.display = "flex";
    
    try {
        showLoading("개인정보 제거 중...");
        
        // Web UI 백엔드 API 호출
        const response = await fetch(API_BASE + "/privacy-removal/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text: originalText,
                prompt_type: promptType
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || "개인정보 제거 실패");
        }
        
        const data = await response.json();
        
        // 결과 처리
        if (data.success) {
            // 결과 표시
            document.getElementById("privacy-result-text").textContent = data.privacy_rm_text;
            document.getElementById("privacy-exist").textContent = 
                data.privacy_exist === "Y" ? "예 🔴" : "아니오 ✅";
            document.getElementById("privacy-reason").textContent = 
                data.exist_reason || "(설명 없음)";
            
            // 비교 데이터 저장
            document.getElementById("privacy-original").value = originalText;
            document.getElementById("privacy-processed").value = data.privacy_rm_text;
            
            // 결과 섹션 표시
            privacyResultSection.style.display = "block";
            
            showNotification("개인정보 제거 완료!", "success");
            console.log("Privacy Removal 결과:", data);
        } else {
            throw new Error(data.error || "처리 실패");
        }
    } catch (error) {
        console.error("개인정보 제거 오류:", error);
        showNotification("개인정보 제거 중 오류가 발생했습니다: " + error.message, "error");
    } finally {
        privacyRemovalBtn.disabled = false;
        privacyProcessing.style.display = "none";
        hideLoading();
    }
}

/**
 * Privacy Removal 결과 복사
 */
function copyPrivacyResult() {
    const resultText = document.getElementById("privacy-result-text").textContent;
    if (!resultText) {
        showNotification("복사할 텍스트가 없습니다", "warning");
        return;
    }
    
    navigator.clipboard.writeText(resultText).then(() => {
        showNotification("복사되었습니다!", "success");
    }).catch(err => {
        showNotification("복사 실패: " + err.message, "error");
    });
}

/**
 * Privacy Removal 결과 다운로드
 */
function downloadPrivacyResult() {
    const resultText = document.getElementById("privacy-result-text").textContent;
    const originalText = document.getElementById("privacy-original").value;
    const privacyExist = document.getElementById("privacy-exist").textContent;
    
    if (!resultText) {
        showNotification("다운로드할 텍스트가 없습니다", "warning");
        return;
    }
    
    const content = `개인정보 제거 결과 보고서
=====================================
생성일시: ${new Date().toLocaleString('ko-KR')}

[원본 텍스트]
${originalText}

[처리된 텍스트]
${resultText}

[개인정보 포함 여부]
${privacyExist}

=====================================
이 파일은 자동으로 생성되었습니다.`;
    
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `privacy_removal_${new Date().getTime()}.txt`;
    link.click();
}

/**
 * 원본/처리 비교 토글
 */
function togglePrivacyComparison() {
    const compView = document.getElementById("privacy-comparison");
    if (compView.style.display === "none") {
        compView.style.display = "block";
    } else {
        compView.style.display = "none";
    }
}

/**
 * 결과 화면에서 Privacy Removal 섹션 표시
 */
function showPrivacyRemovalOptions() {
    privacyRemovalSection.style.display = "block";
    privacyResultSection.style.display = "none";
    privacyRemovalBtn.disabled = false;
}

/**
 * Privacy Removal 섹션 초기화
 */
function resetPrivacyRemovalSection() {
    privacyRemovalSection.style.display = "none";
    privacyResultSection.style.display = "none";
    document.getElementById("privacy-result-text").textContent = "";
    document.getElementById("privacy-exist").textContent = "-";
    document.getElementById("privacy-reason").textContent = "-";
    document.getElementById("privacy-comparison").style.display = "none";
}

// ============================================================================
// 로딩 인디케이터
// ============================================================================

const loadingContainer = document.getElementById("loading-container");
const loadingText = document.getElementById("loading-text");

function showLoading(text = "처리 중...") {
    loadingText.textContent = text;
    loadingContainer.style.display = "flex";
}

function hideLoading() {
    loadingContainer.style.display = "none";
}

// ============================================================================
// 초기화
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
    console.log("STT Web UI 로드됨");
    
    // 파일 업로드 핸들러 초기화 (반드시 먼저)
    initializeFileUploadHandlers();
    
    // 글로벌 백엔드 정보 초기화
    fetchGlobalBackendInfo();
    
    // 글로벌 백엔드 설정 체크박스
    setGlobalBackendCheckbox?.addEventListener("change", () => {
        if (setGlobalBackendCheckbox.checked && !backendSelect.value) {
            showNotification("변경할 백엔드를 먼저 선택해주세요", "warning");
            setGlobalBackendCheckbox.checked = false;
        }
    });
    
    // 백엔드 선택 변경 시
    backendSelect?.addEventListener("change", () => {
        if (setGlobalBackendCheckbox.checked && !backendSelect.value) {
            showNotification("글로벌 백엔드 설정을 해제했습니다", "info");
            setGlobalBackendCheckbox.checked = false;
        }
    });
    
    // Privacy Removal 버튼 이벤트
    privacyRemovalBtn?.addEventListener("click", processPrivacyRemoval);});