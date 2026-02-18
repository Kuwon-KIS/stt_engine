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
 * API 호출 함수
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

    try {
        const response = await fetch(API_BASE + endpoint, options);
        const json = await response.json();

        if (!response.ok) {
            throw new Error(json.error || json.detail || "요청 실패");
        }

        return json;
    } catch (error) {
        console.error("API 호출 실패:", error);
        showNotification(error.message, "error");
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

// 드래그 & 드롭
dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("active");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("active");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("active");
    handleFileSelect(e.dataTransfer.files[0]);
});

dropZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => {
    if (e.target.files.length) {
        handleFileSelect(e.target.files[0]);
    }
});

browseBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    fileInput.click();
});

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
        
        const result = await apiCall("/transcribe/", "POST", {
            file_id: uploadResult.file_id,
            language: language,
            backend: backend,
            is_stream: isStream
        });

        hideLoading();

        // 결과 표시
        displayResult(result);
        showNotification("녹취 분석 완료", "info");

    } catch (error) {
        hideLoading();
        showNotification(`분석 실패: ${error.message}`, "error");
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
    
    // 스크롤
    document.getElementById("result-section").scrollIntoView({ behavior: "smooth" });
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
    element.click();
    document.body.removeChild(element);
    showNotification("파일이 다운로드되었습니다", "info");
});

document.getElementById("download-json-btn")?.addEventListener("click", async () => {
    try {
        const data = await apiCall(`/results/${currentFileId}/export?format=json`);
        const element = document.createElement("a");
        element.setAttribute("href", "data:application/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2)));
        element.setAttribute("download", "result.json");
        element.style.display = "none";
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
        showNotification("파일이 다운로드되었습니다", "info");
    } catch (error) {
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

        const result = await apiCall("/batch/start/", "POST", {
            extension: batchExtensionInput.value || ".wav",
            language: batchLanguageSelect.value,
            parallel_count: parseInt(batchParallelInput.value) || 2
        });

        currentBatchId = result.batch_id;
        showNotification(`배치 처리 시작: ${result.total_files}개 파일`, "info");

        // 진행 상황 모니터링
        document.getElementById("batch-progress-container").style.display = "block";
        startBatchProgressMonitoring(result.batch_id);

    } catch (error) {
        showNotification(`배치 처리 시작 실패: ${error.message}`, "error");
    } finally {
        startBatchBtn.disabled = false;
        startBatchBtn.textContent = "배치 처리 시작";
    }
});

/**
 * 배치 진행 상황 모니터링
 */
function startBatchProgressMonitoring(batchId) {
    clearInterval(batchProgressInterval);

    // 즉시 첫 번째 업데이트
    async function updateProgress() {
        try {
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

            // 파일 상태 업데이트
            updateBatchTableStatus(progress.files);

            // 완료 여부 확인
            if (completed + progress.failed === total) {
                clearInterval(batchProgressInterval);
                showNotification(`배치 처리 완료: ${completed}성공, ${progress.failed}실패`, "info");
            }

        } catch (error) {
            console.error("진행 상황 조회 실패:", error);
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
                resultCell.addEventListener("click", () => {
                    showResultModal(file.name, file.result_text, {
                        duration_sec: file.duration_sec,
                        processing_time_sec: file.processing_time_sec,
                        word_count: file.word_count
                    });
                });
            } else if (file.status === "done" && !file.result_text) {
                resultCell.textContent = "(결과 없음)";
            } else if (file.status === "error") {
                resultCell.innerHTML = `<span style="color: red;">${file.error_message || "에러"}</span>`;
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
    
    // 서버 헬스 체크
    apiCall("/health").then(health => {
        console.log("서버 상태:", health.status);
    }).catch(error => {
        console.error("서버 연결 실패:", error);
    });
});
