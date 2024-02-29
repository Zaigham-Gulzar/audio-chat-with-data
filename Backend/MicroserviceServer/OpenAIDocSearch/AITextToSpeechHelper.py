import os
from config.ExternalConfiguration import ExternalConfiguration
import azure.cognitiveservices.speech as speechsdk

class SpeechSynthesis:
    config = ExternalConfiguration()

    def generte_neural_speech_for_text(self, text: str):
        speech_config = speechsdk.SpeechConfig(subscription=self.config.AZURE_SPEECH_SERVICE_KEY, region=self.config.AZURE_SPEECH_SERVICE_REGION)
        speech_config.speech_synthesis_voice_name=self.config.AZURE_SPEECH_SYNTHESIS_VOICE
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        speech_synthesis_result = speech_synthesizer.speak_text(text)

        if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print("Speech synthesized for text [{}]".format(text))
            return speech_synthesis_result.audio_data
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            print("Speech synthesis canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    print("Error details: {}".format(cancellation_details.error_details))
                    print("Did you set the speech resource key and region values?")