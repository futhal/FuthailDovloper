import requests
from demo.settings import BASE_DIR
from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest

from google.cloud import recaptchaenterprise_v1
from google.cloud.recaptchaenterprise_v1 import Assessment
from google.oauth2 import service_account
from django.urls import reverse

def create_assessment(
    project_id: str, recaptcha_key: str, token: str, recaptcha_action: str
) -> Assessment:
    """Create an assessment to analyze the risk of a UI action.
    Args:
        project_id: Your Google Cloud Project ID.
        recaptcha_key: The reCAPTCHA key associated with the site/app
        token: The generated token obtained from the client.
        recaptcha_action: Action name corresponding to the token.
    """
    # Load credentials from the JSON file
    credentials = service_account.Credentials.from_service_account_file(
        f"{BASE_DIR}/service-account-file.json"
    )

    client = recaptchaenterprise_v1.RecaptchaEnterpriseServiceClient(credentials=credentials)

    # Set the properties of the event to be tracked.
    event = recaptchaenterprise_v1.Event()
    event.site_key = recaptcha_key
    event.token = token

    assessment = recaptchaenterprise_v1.Assessment()
    assessment.event = event

    project_name = f"projects/{project_id}"

    # Build the assessment request.
    request = recaptchaenterprise_v1.CreateAssessmentRequest()
    request.assessment = assessment
    request.parent = project_name

    response = client.create_assessment(request)

    # Check if the token is valid.
    if not response.token_properties.valid:
        print(
            "The CreateAssessment call failed because the token was "
            + "invalid for the following reasons: "
            + str(response.token_properties.invalid_reason)
        )
        return None

    # Check if the expected action was executed.
    if response.token_properties.action != recaptcha_action:
        print(
            "The action attribute in your reCAPTCHA tag does"
            + "not match the action you are expecting to score"
        )
        return None

    # Get the risk score and the reason(s).
    for reason in response.risk_analysis.reasons:
        print(reason)
    print(
        "The reCAPTCHA score for this token is: "
        + str(response.risk_analysis.score)
    )

    # Get the assessment name (id). Use this to annotate the assessment.
    assessment_name = client.parse_assessment_path(response.name).get("assessment")
    print(f"Assessment name: {assessment_name}")
    
    return response
from django.middleware.csrf import get_token

def social_login_view(request):
    if request.method == "POST":
        token = request.POST.get("g-recaptcha-response")
        provider = request.POST.get("provider")
        
        if token and provider:
            # احصل على URL تسجيل الدخول لـ Google
            google_login_url = reverse('google_login')
            
            # توليد csrfmiddlewaretoken جديدة
            csrf_token = get_token(request)

            # إعداد البيانات للإرسال باستخدام POST
            data = {
                'csrfmiddlewaretoken': csrf_token,
                # أضف أي بيانات أخرى تحتاجها في طلب POST
            }

            # إعداد ملف تعريف الارتباط CSRF
            cookies = {
                'csrftoken': csrf_token
            }

            # إرسال طلب POST إلى Google مع تضمين ملف تعريف الارتباط CSRF
            response = requests.post(request.build_absolute_uri(google_login_url), data=data, cookies=cookies)

            # إعادة التوجيه إلى استجابة تسجيل الدخول الخاصة بـ Google
            return redirect(response.url)
            # return redirect(f'/accounts/{provider}/login/')
            # response = create_assessment(
            #     project_id="firm-star-433219-q6",
            #     recaptcha_key="6LeZ9DIqAAAAAI78HSwTQo51YBHgYfQe2DUUhKuk",
            #     token=token,
            #     recaptcha_action="SOCIAL_LOGIN",  # يمكنك تخصيص هذه العملية للتفريق بينها وبين تسجيل الدخول العادي
            # )
            # if response and response.token_properties.valid and response.token_properties.action == "SOCIAL_LOGIN":
            #     # تابع عملية تسجيل الدخول بالحساب الاجتماعي
            #     return redirect('google_login')
            # else:
            #     # عرض رسالة خطأ أو إعادة المحاولة
            #     return HttpResponseBadRequest("Invalid reCAPTCHA token.")
        else:
            return HttpResponseBadRequest("No reCAPTCHA token or provider provided.")
    
    return render(request, 'account/login.html')
