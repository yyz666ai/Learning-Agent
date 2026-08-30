import json
from pathlib import Path

from backend import main
from backend.onboarding import OnboardingSubmission


def test_diagnosis_uses_current_intent_and_bounded_generation(tmp_path, monkeypatch):
    user = tmp_path / 'userdir/u_test/onboarding'
    user.mkdir(parents=True)
    (user / 'intent-state.json').write_text(json.dumps({'slots': {'topic': '前端', 'tech_stack': ['Vue']}}))
    monkeypatch.setattr(main, 'latest_release', lambda: Path('/fixture'))
    seen = {}
    def model(uid, prompt, release, **kwargs):
        seen.update(prompt=prompt, **kwargs)
        return json.dumps({'topic': '前端', 'questions': [
            dict(id=f'q{i}', prompt=f'前端 Vue 问题 {i}', dimension='前端',
                 options=[dict(id='a', label='甲'), dict(id='b', label='乙')], correct_option_id='b')
            for i in range(3)]})
    monkeypatch.setattr(main, 'chat', model)
    request = OnboardingSubmission.model_validate(dict(user_id='test', topic={'type':'custom','value':'前端'},
        level_claim='some', learning_mode='practice', goal_route='interview_sprint', session_minutes=25))
    result = main._generate_diagnostic_session(request, lambda _: None, server_root=tmp_path)
    assert result['diagnostic_source'] == 'skill_generated'
    assert seen.get('generation') == 'diagnosis'
    assert 'Vue' in seen['prompt']
    assert seen['timeout'] == 120
