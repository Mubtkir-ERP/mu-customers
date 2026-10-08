# نظام "رابط الدخول السريع" (Quick Login Link)
# ------------------------------------------------------------------
# الفكرة: بدل وضع اسم المستخدم وكلمة السر في الرابط (غير آمن)، نولّد
# رمزاً عشوائياً مؤقتاً (token). الرابط يحمل الرمز فقط. الخادم يتحقق
# من الرمز ثم ينشئ جلسة Frappe آمنة للموظف ويحوّله للداخل.
#
# الأمان:
#   - لا تُخزَّن كلمة السر إطلاقاً.
#   - في قاعدة البيانات نخزّن "بصمة" الرمز (hash) لا الرمز نفسه،
#     فحتى لو تسرّبت القاعدة لا يُستخرَج الرابط.
#   - الإنشاء مقصور على Administrator (أو من يملك صلاحية كتابة User).
#   - قابل للإلغاء فوراً من زر "إلغاء الرابط".
#   - مدة صلاحية قابلة للضبط؛ القيمة 0 = دائم حتى الإلغاء اليدوي.

import frappe
import hashlib
import secrets
from frappe import _
from frappe.utils import now_datetime, add_to_date, get_url

# المسار العام الذي يفتحه الموظف: نقطة الـ API للدالة login أدناه.
# نوجّه الرابط مباشرة إلى /api/method/... لأنها تُنفّذ كود بايثون وتُحوّل،
# بينما website_route_rules مخصّصة لصفحات الويب لا للدوال.
LOGIN_LINK_ROUTE = "/api/method/mu_customers.login_link.login"

# طول الرمز العشوائي (بالبايت قبل التحويل لنص). 32 بايت = قوة عالية جداً.
TOKEN_BYTES = 32


def _hash(token: str) -> str:
	"""بصمة SHA-256 للرمز. نخزّن هذه البصمة لا الرمز الأصلي."""
	return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------
# 1) توليد الرابط  (يُستدعى من زر "إنشاء رابط دخول سريع" في مستند User)
# ------------------------------------------------------------------
@frappe.whitelist()
def generate(user: str, validity_days=None):
	"""تولّد رمزاً جديداً لمستخدم وتُرجع الرابط الكامل.

	الصلاحية: Administrator فقط، أو من يملك صلاحية كتابة على User.
	validity_days: عدد أيام الصلاحية. 0 أو فارغ = دائم حتى الإلغاء.
	"""
	_ensure_can_manage()

	if not user or not frappe.db.exists("User", user):
		frappe.throw(_("المستخدم غير موجود"))

	# منع توليد رابط لحسابات النظام الحسّاسة.
	if user in ("Administrator", "Guest"):
		frappe.throw(_("لا يمكن إنشاء رابط دخول سريع لهذا الحساب"))

	user_doc = frappe.get_doc("User", user)
	if not user_doc.enabled:
		frappe.throw(_("حساب المستخدم معطّل"))

	# تحديد المدة: نقرأ من الوسيط، وإلا من حقل المستخدم، وإلا 0 (دائم).
	if validity_days is None or validity_days == "":
		validity_days = user_doc.get("custom_login_link_validity_days") or 0
	validity_days = int(validity_days or 0)
	if validity_days < 0:
		validity_days = 0

	# الرمز الأصلي يظهر مرة واحدة فقط (في الرابط)، ولا يُخزَّن.
	token = secrets.token_urlsafe(TOKEN_BYTES)

	expiry = None
	if validity_days > 0:
		expiry = add_to_date(now_datetime(), days=validity_days)

	# نخزّن البصمة + تاريخ الانتهاء + المدة المختارة على المستخدم.
	frappe.db.set_value(
		"User",
		user,
		{
			"custom_login_link_hash": _hash(token),
			"custom_login_link_expiry": expiry,
			"custom_login_link_validity_days": validity_days,
		},
		update_modified=False,
	)
	frappe.db.commit()

	link = get_url(f"{LOGIN_LINK_ROUTE}?token={token}")

	return {
		"link": link,
		"user": user,
		"full_name": user_doc.full_name,
		"expiry": str(expiry) if expiry else None,
		"validity_days": validity_days,
		"permanent": validity_days == 0,
	}


# ------------------------------------------------------------------
# 2) إلغاء الرابط  (زر "إلغاء الرابط")
# ------------------------------------------------------------------
@frappe.whitelist()
def revoke(user: str):
	"""تُبطل أي رابط قائم للمستخدم فوراً، دون المساس بكلمة سره."""
	_ensure_can_manage()

	if not user or not frappe.db.exists("User", user):
		frappe.throw(_("المستخدم غير موجود"))

	frappe.db.set_value(
		"User",
		user,
		{
			"custom_login_link_hash": None,
			"custom_login_link_expiry": None,
		},
		update_modified=False,
	)
	frappe.db.commit()

	return {"revoked": True, "user": user}


# ------------------------------------------------------------------
# 3) حالة الرابط  (لعرضها في النموذج: هل يوجد رابط فعّال؟)
# ------------------------------------------------------------------
@frappe.whitelist()
def status(user: str):
	"""يُرجع حالة الرابط الحالي للمستخدم (موجود/منتهٍ/لا يوجد)."""
	_ensure_can_manage()

	if not user or not frappe.db.exists("User", user):
		return {"exists": False}

	vals = frappe.db.get_value(
		"User",
		user,
		["custom_login_link_hash", "custom_login_link_expiry"],
		as_dict=True,
	)
	if not vals or not vals.custom_login_link_hash:
		return {"exists": False}

	expired = False
	if vals.custom_login_link_expiry:
		expired = now_datetime() > frappe.utils.get_datetime(vals.custom_login_link_expiry)

	return {
		"exists": True,
		"expired": expired,
		"expiry": str(vals.custom_login_link_expiry) if vals.custom_login_link_expiry else None,
		"permanent": not vals.custom_login_link_expiry,
	}


# ------------------------------------------------------------------
# 4) استهلاك الرابط  (نقطة الدخول العامة التي يفتحها الموظف)
# ------------------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def login(**kwargs):
	"""نقطة النهاية العامة. تستقبل ?token=... من الرابط.

	تتحقق من البصمة ومن الصلاحية، ثم تنشئ جلسة Frappe للموظف وتحوّله
	إلى لوحة التحكم. لا تكشف أبداً أي سبب تفصيلي للفشل (حماية).
	"""
	token = kwargs.get("token") or frappe.form_dict.get("token")

	if not token:
		return _deny()

	token_hash = _hash(token)

	# نبحث عن المستخدم صاحب هذه البصمة. فهرس على الحقل يجعلها سريعة.
	user = frappe.db.get_value(
		"User",
		{"custom_login_link_hash": token_hash, "enabled": 1},
		"name",
	)

	if not user or user in ("Administrator", "Guest"):
		return _deny()

	# تحقق من انتهاء الصلاحية.
	expiry = frappe.db.get_value("User", user, "custom_login_link_expiry")
	if expiry and now_datetime() > frappe.utils.get_datetime(expiry):
		return _deny()

	# إنشاء الجلسة الآمنة للموظف.
	frappe.local.login_manager.login_as(user)
	frappe.local.login_manager.post_login()

	# تحويل إلى لوحة التحكم (أو الصفحة الرئيسية للموقع).
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/app"


def _deny():
	"""رد موحّد عند الفشل: تحويل إلى صفحة الدخول العادية دون تلميح للسبب."""
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/login"


def _ensure_can_manage():
	"""لا يسمح إلا لـ Administrator أو من يملك صلاحية كتابة على User."""
	if frappe.session.user == "Administrator":
		return
	if frappe.has_permission("User", "write"):
		return
	frappe.throw(_("غير مصرّح لك بإنشاء روابط دخول"), frappe.PermissionError)
