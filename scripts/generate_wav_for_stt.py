from gtts import gTTS
from pydub import AudioSegment
import io

def create_korean_wav(text, filename="test_ko.wav"):
    print(f"'{text}' 문구로 음성 생성을 시작합니다...")
    
    # 1. gTTS를 사용하여 MP3 데이터를 메모리(BytesIO)에 바로 생성
    tts = gTTS(text=text, lang='ko')
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)

    # 2. pydub을 사용하여 MP3 데이터를 로드
    audio = AudioSegment.from_file(mp3_fp, format="mp3")

    # 3. STT 최적화 설정 (16kHz, Mono, 16-bit)
    # 저사양 서버에서 리샘플링 부하를 줄이기 위해 미리 변환합니다.
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

    # 4. WAV 파일로 저장
    audio.export(filename, format="wav")
    print(f"성공적으로 저장되었습니다: {filename}")

if __name__ == "__main__":
    # 테스트할 짧은 한국어 문장
    test_text = "안녕하세요. 저사양 서버에서 진행하는 음성 인식 테스트 파일입니다."
    test_text = """
        안녕하세요. 현재 음성 인식 성능을 확인하기 위한 테스트를 진행하고 있습니다. 이 서버는 사양이 다소 제한적이라서 메모리 점유율을 사 기가바이트 이하로 유지하는 것이 매우 중요합니다.
        오늘은 2026년 2월 10일이고, 서울의 날씨는 조금 쌀쌀한 편입니다. 기술적인 관점에서 보면, 위스퍼 모델의 타이니 버전이나 베이스 버전을 활용해서 한국어 인식률이 얼마나 정확하게 나오는지 확인해 보려고 합니다. 특히 도커 환경이나 폐쇄망 서버에서 온프레미스로 모델을 구동할 때 발생할 수 있는 메모리 누수나 처리 속도 지연 문제를 면밀히 검토할 예정입니다.
        텐서알티 엘엘엠이나 파스너 위스퍼 같은 최적화 도구들이 실제 환경에서 어느 정도 효율을 보여줄까요? 숫자 일, 이, 삼, 사와 영문 대문자 에이, 비, 씨도 잘 인식하는지 궁금하네요. 이상으로 1분 분량의 음성 인식 테스트 데이터 생성을 마치겠습니다. 감사합니다.
    """
    create_korean_wav(test_text, 'test_ko_1min.wav')
