# Web UI - Privacy Removal 기능 통합 계획

## 📋 Overview

이 문서는 Privacy Removal 기능을 Web UI에서 trigger할 수 있도록 통합하는 방법을 설명합니다.

**목표:**
```
STT 결과 → 개인정보 제거 버튼 클릭 → Privacy Removal API 호출 → 정제된 결과 표시
```

---

## 🎯 전체 프로세스 Flow

### 사용자 관점

```
1. Web UI 접속 (http://localhost:8100)
        ↓
2. 음성 파일 업로드
        ↓
3. STT 처리 완료 (STT Engine)
        ↓
4. 결과 화면에서:
   - 원본 텍스트 표시
   - "개인정보 제거" 버튼 표시 ✨
   - 프롬프트 타입 선택 가능 (optional)
        ↓
5. "개인정보 제거" 클릭
        ↓
6. Privacy Removal 처리 (vLLM)
        ↓
7. 정제된 텍스트 표시
```

### 기술 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│ Web UI Frontend (포트 8100)                              │
│ ┌────────────────────────────────────────────────────┐  │
│ │ index.html                                         │  │
│ │ - 파일 업로드 폼                                    │  │
│ │ - STT 결과 표시                                    │  │
│ │ - Privacy Removal UI ✨                            │  │
│ │   └─ 버튼, 체크박스, 드롭다운                      │  │
│ └────────────────────────────────────────────────────┘  │
│           ↓ (JavaScript 비동기 호출)                    │
│ ┌────────────────────────────────────────────────────┐  │
│ │ main.js                                            │  │
│ │ - API 호출 함수                                    │  │
│ │ - 결과 처리 및 UI 업데이트                         │  │
│ └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
        ↓ (REST API HTTP POST)
┌──────────────────────────────────────────────────────────┐
│ Web UI Backend (포트 8100)                               │
│ ┌────────────────────────────────────────────────────┐  │
│ │ main.py                                            │  │
│ │ - @app.post("/api/privacy-removal/") ✨          │  │
│ │ - STT Engine API 호출 위임                        │  │
│ └────────────────────────────────────────────────────┘  │
│           ↓ (HTTP 포워드)                               │
│ ┌────────────────────────────────────────────────────┐  │
│ │ services/stt_service.py                            │  │
│ │ - privacy_removal_process() ✨                     │  │
│ │ - STT Engine의 privacy-removal 엔드포인트 호출    │  │
│ └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
        ↓ (HTTP POST)
┌──────────────────────────────────────────────────────────┐
│ STT Engine (포트 8003)                                   │
│ ┌────────────────────────────────────────────────────┐  │
│ │ POST /api/privacy-removal/process                 │  │
│ │ - vLLM 기반 처리                                  │  │
│ │ - 개인정보 탐지 및 마스킹                         │  │
│ └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 💻 구현 상세

### 1. Frontend - HTML 업데이트

**파일:** `web_ui/templates/index.html`

추가할 UI 요소:

```html
<!-- STT 결과 섹션 (기존) -->
<div id="resultsSection" style="display:none;">
    <h2>STT 결과</h2>
    <textarea id="sttResult" readonly></textarea>
    
    <!-- Privacy Removal 옵션 (신규) ✨ -->
    <div id="privacyRemovalSection" style="margin-top: 20px;">
        <h3>개인정보 제거</h3>
        <p>인식된 텍스트에서 개인정보를 자동으로 마스킹할 수 있습니다.</p>
        
        <!-- 프롬프트 타입 선택 -->
        <div>
            <label for="promptType">프롬프트 타입:</label>
            <select id="promptType">
                <option value="privacy_remover_default_v6">기본 (개인정보 마스킹)</option>
            </select>
        </div>
        
        <!-- 버튼 -->
        <button id="privacyRemovalBtn" onclick="processPrivacyRemoval()">
            개인정보 제거
        </button>
        
        <!-- 처리 중 표시 -->
        <div id="privacyProcessing" style="display:none;">
            <p>개인정보 제거 중...</p>
            <progress></progress>
        </div>
    </div>
    
    <!-- 처리된 결과 -->
    <div id="privacyResultSection" style="display:none; margin-top: 20px;">
        <h3>처리된 결과</h3>
        <textarea id="privacyResult" readonly></textarea>
        
        <!-- 비교 보기 -->
        <button onclick="toggleComparison()">원본/처리 비교</button>
        <div id="comparisonView" style="display:none; margin-top: 10px;">
            <div style="float:left; width:48%;">
                <h4>원본</h4>
                <textarea id="originalText" readonly style="width:100%; height:200px;"></textarea>
            </div>
            <div style="float:right; width:48%;">
                <h4>처리됨</h4>
                <textarea id="processedText" readonly style="width:100%; height:200px;"></textarea>
            </div>
            <div style="clear:both;"></div>
        </div>
    </div>
</div>
```

**CSS (추가):**

```css
#privacyRemovalSection {
    border: 1px solid #ddd;
    padding: 15px;
    border-radius: 5px;
    background-color: #f9f9f9;
}

#privacyResultSection {
    border: 2px solid #4CAF50;
    padding: 15px;
    border-radius: 5px;
    background-color: #f1f8f4;
}

#privacyProcessing {
    padding: 10px;
    background-color: #fff3cd;
    border: 1px solid #ffc107;
    border-radius: 4px;
    color: #856404;
}

button#privacyRemovalBtn {
    background-color: #4CAF50;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    margin-top: 10px;
}

button#privacyRemovalBtn:hover {
    background-color: #45a049;
}

button#privacyRemovalBtn:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
}
```

---

### 2. Frontend - JavaScript 로직

**파일:** `web_ui/static/js/main.js`

추가할 함수:

```javascript
/**
 * Privacy Removal 처리 시작
 */
async function processPrivacyRemoval() {
    const originalText = document.getElementById("sttResult").value;
    
    if (!originalText.trim()) {
        alert("먼저 STT 결과를 생성해주세요.");
        return;
    }
    
    const promptType = document.getElementById("promptType").value;
    
    // UI 업데이트
    const btn = document.getElementById("privacyRemovalBtn");
    const processing = document.getElementById("privacyProcessing");
    
    btn.disabled = true;
    processing.style.display = "block";
    
    try {
        // Web UI 백엔드 API 호출
        const response = await fetch("/api/privacy-removal/", {
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
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // 결과 처리
        if (data.success) {
            // 결과 표시
            document.getElementById("privacyResult").value = data.privacy_rm_text;
            document.getElementById("originalText").value = originalText;
            document.getElementById("processedText").value = data.privacy_rm_text;
            
            // 결과 섹션 표시
            document.getElementById("privacyResultSection").style.display = "block";
            
            // 정보 표시
            console.log("Privacy Removal 결과:");
            console.log("- 개인정보 포함:", data.privacy_exist);
            console.log("- 사유:", data.exist_reason);
        } else {
            throw new Error(data.error || "처리 실패");
        }
    } catch (error) {
        console.error("오류:", error);
        alert("개인정보 제거 중 오류가 발생했습니다:\n" + error.message);
    } finally {
        btn.disabled = false;
        processing.style.display = "none";
    }
}

/**
 * 원본/처리 비교 토글
 */
function toggleComparison() {
    const compView = document.getElementById("comparisonView");
    if (compView.style.display === "none") {
        compView.style.display = "block";
    } else {
        compView.style.display = "none";
    }
}

/**
 * STT 완료 후 Privacy Removal 섹션 표시
 * (기존 transcribe 함수 내에 추가)
 */
function showPrivacyRemovalOptions() {
    document.getElementById("privacyRemovalSection").style.display = "block";
}
```

**기존 transcribe 함수에 추가:**

```javascript
// transcribe 함수 내에서 결과 받은 후
if (data.success) {
    document.getElementById("sttResult").value = data.text;
    document.getElementById("resultsSection").style.display = "block";
    
    // Privacy Removal 옵션 표시 ✨
    showPrivacyRemovalOptions();
}
```

---

### 3. Backend - API 라우트 추가

**파일:** `web_ui/main.py`

추가할 라우트:

```python
@app.post("/api/privacy-removal/")
async def privacy_removal(request: dict):
    """
    Privacy Removal 처리
    
    Request:
    {
        "text": "처리할 텍스트",
        "prompt_type": "privacy_remover_default_v6"
    }
    
    Response:
    {
        "success": true,
        "privacy_exist": "Y/N",
        "exist_reason": "개인정보 발견 이유",
        "privacy_rm_text": "처리된 텍스트"
    }
    """
    try:
        text = request.get("text", "")
        prompt_type = request.get("prompt_type", "privacy_remover_default_v6")
        
        if not text.strip():
            return {
                "success": False,
                "error": "텍스트가 비어있습니다"
            }
        
        # STT Service를 통해 Privacy Removal 처리
        result = await stt_service.process_privacy_removal(
            text=text,
            prompt_type=prompt_type
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Privacy Removal 처리 오류: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

---

### 4. Backend - Service 메서드 추가

**파일:** `web_ui/services/stt_service.py`

추가할 메서드:

```python
async def process_privacy_removal(self, text: str, prompt_type: str = "privacy_remover_default_v6") -> dict:
    """
    Privacy Removal 처리
    
    Args:
        text: 처리할 텍스트
        prompt_type: 사용할 프롬프트 타입
    
    Returns:
        {
            "success": bool,
            "privacy_exist": "Y/N",
            "exist_reason": str,
            "privacy_rm_text": str
        }
    """
    try:
        # STT Engine의 Privacy Removal 엔드포인트 호출
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/api/privacy-removal/process"
            
            payload = {
                "text": text,
                "prompt_type": prompt_type
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=300)  # 5분 타임아웃
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"STT Engine 오류: {response.status} - {error_text}")
                    return {
                        "success": False,
                        "error": f"STT Engine 오류: {response.status}",
                        "privacy_rm_text": text  # Fallback: 원본 텍스트 반환
                    }
    
    except asyncio.TimeoutError:
        logger.error("Privacy Removal 타임아웃")
        return {
            "success": False,
            "error": "처리 타임아웃",
            "privacy_rm_text": text
        }
    except Exception as e:
        logger.error(f"Privacy Removal 오류: {e}")
        return {
            "success": False,
            "error": str(e),
            "privacy_rm_text": text
        }
```

---

## 📊 Data Models

### Request Model (선택사항)

**파일:** `web_ui/models/schemas.py` (필요시)

```python
from pydantic import BaseModel

class PrivacyRemovalRequest(BaseModel):
    text: str
    prompt_type: str = "privacy_remover_default_v6"
```

### Response Structure

STT Engine이 반환하는 형식:

```json
{
    "success": true,
    "privacy_exist": "Y",
    "exist_reason": "이름(John Smith), 전화번호(010-1234-5678)",
    "privacy_rm_text": "나는 J*** S*****이고 010-****-****입니다"
}
```

---

## 🧪 테스트 계획

### Manual Testing

```bash
# 1. Web UI 시작
docker run -p 8100:8100 stt-web-ui:latest

# 2. STT Engine이 준비되어 있는지 확인
curl http://localhost:8003/health

# 3. Privacy Removal 엔드포인트 확인
curl http://localhost:8003/api/privacy-removal/prompts

# 4. Web UI에서 테스트
# - 브라우저에서 http://localhost:8100 접속
# - 음성 파일 업로드
# - STT 결과 확인
# - "개인정보 제거" 버튼 클릭
# - 결과 확인
```

### Automated Testing

```python
# test_privacy_removal_web_ui.py
import requests
import json

def test_privacy_removal_via_web_ui():
    """Web UI 경유 Privacy Removal 테스트"""
    
    # 1. Web UI API 호출
    response = requests.post(
        "http://localhost:8100/api/privacy-removal/",
        headers={"Content-Type": "application/json"},
        json={
            "text": "나는 John Smith이고 010-1234-5678입니다",
            "prompt_type": "privacy_remover_default_v6"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "J***" in data["privacy_rm_text"]
    print("✅ Web UI Privacy Removal 테스트 성공")

if __name__ == "__main__":
    test_privacy_removal_via_web_ui()
```

---

## 🚀 배포 순서

### Step 1: STT Engine 배포 (선행 조건)

```bash
# 1. STT Engine 빌드
bash build-engine-image.sh

# 2. STT Engine 시작
docker run -p 8003:8003 stt-engine:latest

# 3. 상태 확인
curl http://localhost:8003/health
```

### Step 2: Web UI 코드 수정

- [ ] `web_ui/templates/index.html` 수정
- [ ] `web_ui/static/js/main.js` 수정
- [ ] `web_ui/main.py` 수정
- [ ] `web_ui/services/stt_service.py` 수정

### Step 3: Web UI 빌드 및 배포

```bash
# 1. Web UI 빌드
docker build -t stt-web-ui:latest web_ui/

# 2. Web UI 시작
docker run -p 8100:8100 stt-web-ui:latest

# 3. 테스트
curl http://localhost:8100/

# 4. 수동 테스트
# 브라우저에서 http://localhost:8100 접속
```

---

## 📝 체크리스트

### Before Implementation
- [ ] STT Engine이 Privacy Removal 엔드포인트 제공 확인
- [ ] vLLM 서비스가 실행 중인지 확인

### Implementation
- [ ] HTML 템플릿 업데이트
- [ ] JavaScript 함수 추가
- [ ] Python 라우트 추가
- [ ] Service 메서드 추가

### Testing
- [ ] STT 결과 생성 테스트
- [ ] Privacy Removal 버튼 작동 테스트
- [ ] 오류 처리 테스트
- [ ] 브라우저 호환성 테스트

### Deployment
- [ ] Web UI 이미지 빌드
- [ ] Docker 배포
- [ ] 최종 통합 테스트

---

## ⚠️ 주의사항

1. **vLLM 의존성**
   - Privacy Removal은 vLLM 서비스에 의존
   - vLLM이 없으면 처리 실패
   - 사전에 vLLM이 실행 중인지 확인

2. **타임아웃**
   - Privacy Removal 처리는 시간이 소요될 수 있음
   - 타임아웃 설정: 5분 (300초)
   - 필요시 조정

3. **에러 처리**
   - 실패해도 원본 텍스트는 반환 (안정성)
   - UI는 성공/실패 상태 표시

4. **성능**
   - 긴 텍스트는 처리 시간 증가
   - 사용자에게 진행 상황 표시 필수

---

## 📚 관련 문서

- [PRIVACY_REMOVAL_GUIDE.md](PRIVACY_REMOVAL_GUIDE.md) - Privacy Removal 기능 개요
- [WEB_UI_ARCHITECTURE.md](WEB_UI_ARCHITECTURE.md) - Web UI 구조
- [API_USAGE_GUIDE.md](API_USAGE_GUIDE.md) - API 사용법

---

**Document Version:** 1.0
**Last Updated:** 2026년 2월
**Status:** Planning ✏️

For implementation questions, refer to related documentation or GitHub issues.
