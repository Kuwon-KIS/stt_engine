/**
 * 배치 성능 표시 관련 함수
 */

/**
 * 배치 파일의 성능 상세 정보 표시
 */
function showBatchPerformanceDetail(file) {
    if (!file.performance) {
        showNotification("성능 데이터가 없습니다", "warning");
        return;
    }
    
    const perf = file.performance;
    
    const modalContent = `
        <div style="padding: 1.5rem;">
            <h3 style="margin-top: 0; margin-bottom: 1.5rem; color: var(--primary-color);">
                📊 ${file.name} - 성능 상세 정보
            </h3>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
                <!-- CPU 섹션 -->
                <div style="border: 1px solid #e2e8f0; border-radius: 0.375rem; padding: 1rem; background: #f8fafc;">
                    <h4 style="margin: 0 0 0.75rem 0; color: #1e293b; font-size: 0.95rem;">💻 CPU 사용률</h4>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span style="color: #64748b;">평균:</span>
                        <strong style="color: #0ea5e9;">${perf.cpu_percent_avg?.toFixed(1)}%</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #64748b;">최대:</span>
                        <strong style="color: #f59e0b;">${perf.cpu_percent_max?.toFixed(1)}%</strong>
                    </div>
                </div>
                
                <!-- RAM 섹션 -->
                <div style="border: 1px solid #e2e8f0; border-radius: 0.375rem; padding: 1rem; background: #f8fafc;">
                    <h4 style="margin: 0 0 0.75rem 0; color: #1e293b; font-size: 0.95rem;">💾 메모리 (RAM)</h4>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span style="color: #64748b;">평균:</span>
                        <strong style="color: #10b981;">${perf.ram_mb_avg?.toFixed(0)} MB</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #64748b;">피크:</span>
                        <strong style="color: #ef4444;">${perf.ram_mb_peak?.toFixed(0)} MB</strong>
                    </div>
                </div>
                
                <!-- GPU 섹션 -->
                <div style="border: 1px solid #e2e8f0; border-radius: 0.375rem; padding: 1rem; background: #f8fafc;">
                    <h4 style="margin: 0 0 0.75rem 0; color: #1e293b; font-size: 0.95rem;">⚡ GPU VRAM</h4>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span style="color: #64748b;">현재:</span>
                        <strong style="color: #8b5cf6;">${perf.gpu_vram_mb_current?.toFixed(0)} MB</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #64748b;">피크:</span>
                        <strong style="color: #d946ef;">${perf.gpu_vram_mb_peak?.toFixed(0)} MB</strong>
                    </div>
                </div>
                
                <!-- GPU 유틸 섹션 -->
                <div style="border: 1px solid #e2e8f0; border-radius: 0.375rem; padding: 1rem; background: #f8fafc;">
                    <h4 style="margin: 0 0 0.75rem 0; color: #1e293b; font-size: 0.95rem;">🎮 GPU 유틸리티</h4>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #64748b;">사용률:</span>
                        <strong style="color: #06b6d4;">${perf.gpu_percent?.toFixed(1)}%</strong>
                    </div>
                </div>
            </div>
            
            <!-- 처리 시간 -->
            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 0.75rem 1rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                <strong style="color: #92400e;">처리 시간:</strong>
                <span style="margin-left: 0.5rem; color: #b45309;">${perf.processing_time_sec?.toFixed(2)}초</span>
            </div>
            
            <button class="btn btn-secondary" onclick="this.parentElement.parentElement.style.display='none';">닫기</button>
        </div>
    `;
    
    // 모달 컨테이너 생성 또는 재사용
    let modal = document.getElementById("batch-perf-modal");
    if (!modal) {
        modal = document.createElement("div");
        modal.id = "batch-perf-modal";
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        `;
        modal.innerHTML = `
            <div style="
                background: white;
                border-radius: 0.5rem;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                max-width: 600px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
            " id="modal-content"></div>
        `;
        document.body.appendChild(modal);
    }
    
    document.getElementById("modal-content").innerHTML = modalContent;
    modal.style.display = "flex";
    
    // 모달 외부 클릭 시 닫기
    modal.onclick = (e) => {
        if (e.target === modal) {
            modal.style.display = "none";
        }
    };
}

/**
 * 배치 성능 통계 계산 및 표시
 */
function showBatchPerformanceSummary(batchId) {
    // 진행 상황 조회 후 성능 통계 계산
    apiCall(`/batch/progress?batch_id=${batchId}`)
        .then(data => {
            if (!data.files || data.files.length === 0) {
                showNotification("성능 데이터가 없습니다", "warning");
                return;
            }
            
            // 성능 데이터 필터링 및 통계 계산
            const perfData = data.files
                .filter(f => f.performance)
                .map(f => f.performance);
            
            if (perfData.length === 0) {
                showNotification("성능 데이터가 없습니다", "warning");
                return;
            }
            
            // 평균값 계산
            const avgCpu = perfData.reduce((sum, p) => sum + (p.cpu_percent_avg || 0), 0) / perfData.length;
            const maxCpu = Math.max(...perfData.map(p => p.cpu_percent_max || 0));
            const avgRam = perfData.reduce((sum, p) => sum + (p.ram_mb_avg || 0), 0) / perfData.length;
            const peakRam = Math.max(...perfData.map(p => p.ram_mb_peak || 0));
            const avgGpuPercent = perfData.reduce((sum, p) => sum + (p.gpu_percent || 0), 0) / perfData.length;
            const totalTime = perfData.reduce((sum, p) => sum + (p.processing_time_sec || 0), 0);
            
            const modalContent = `
                <div style="padding: 1.5rem;">
                    <h3 style="margin-top: 0; margin-bottom: 1.5rem; color: var(--primary-color);">
                        📈 배치 성능 통계 요약
                    </h3>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
                        <div style="border: 1px solid #e2e8f0; border-radius: 0.375rem; padding: 1rem; background: #f8fafc;">
                            <h4 style="margin: 0 0 0.75rem 0; color: #1e293b; font-size: 0.95rem;">💻 CPU</h4>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span style="color: #64748b;">평균:</span>
                                <strong style="color: #0ea5e9;">${avgCpu.toFixed(1)}%</strong>
                            </div>
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: #64748b;">최대:</span>
                                <strong style="color: #f59e0b;">${maxCpu.toFixed(1)}%</strong>
                            </div>
                        </div>
                        
                        <div style="border: 1px solid #e2e8f0; border-radius: 0.375rem; padding: 1rem; background: #f8fafc;">
                            <h4 style="margin: 0 0 0.75rem 0; color: #1e293b; font-size: 0.95rem;">💾 메모리</h4>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span style="color: #64748b;">평균:</span>
                                <strong style="color: #10b981;">${avgRam.toFixed(0)} MB</strong>
                            </div>
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: #64748b;">피크:</span>
                                <strong style="color: #ef4444;">${peakRam.toFixed(0)} MB</strong>
                            </div>
                        </div>
                        
                        <div style="border: 1px solid #e2e8f0; border-radius: 0.375rem; padding: 1rem; background: #f8fafc;">
                            <h4 style="margin: 0 0 0.75rem 0; color: #1e293b; font-size: 0.95rem;">⚡ GPU 유틸</h4>
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: #64748b;">평균:</span>
                                <strong style="color: #06b6d4;">${avgGpuPercent.toFixed(1)}%</strong>
                            </div>
                        </div>
                        
                        <div style="border: 1px solid #e2e8f0; border-radius: 0.375rem; padding: 1rem; background: #f8fafc;">
                            <h4 style="margin: 0 0 0.75rem 0; color: #1e293b; font-size: 0.95rem;">⏱️ 총 처리시간</h4>
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: #64748b;">전체:</span>
                                <strong style="color: #8b5cf6;">${totalTime.toFixed(1)}초</strong>
                            </div>
                        </div>
                    </div>
                    
                    <div style="background: #dcfce7; border-left: 4px solid #22c55e; padding: 0.75rem 1rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                        <strong style="color: #166534;">파일 수:</strong>
                        <span style="margin-left: 0.5rem; color: #16a34a;">${perfData.length}개</span>
                    </div>
                    
                    <button class="btn btn-secondary" onclick="this.parentElement.parentElement.style.display='none';">닫기</button>
                </div>
            `;
            
            // 모달 컨테이너 생성 또는 재사용
            let modal = document.getElementById("batch-perf-summary-modal");
            if (!modal) {
                modal = document.createElement("div");
                modal.id = "batch-perf-summary-modal";
                modal.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                    display: none;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                `;
                modal.innerHTML = `
                    <div style="
                        background: white;
                        border-radius: 0.5rem;
                        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                        max-width: 600px;
                        width: 90%;
                        max-height: 80vh;
                        overflow-y: auto;
                    " id="modal-summary-content"></div>
                `;
                document.body.appendChild(modal);
            }
            
            document.getElementById("modal-summary-content").innerHTML = modalContent;
            modal.style.display = "flex";
            
            // 모달 외부 클릭 시 닫기
            modal.onclick = (e) => {
                if (e.target === modal) {
                    modal.style.display = "none";
                }
            };
        })
        .catch(error => {
            showNotification(`성능 통계 조회 실패: ${error.message}`, "error");
        });
}
