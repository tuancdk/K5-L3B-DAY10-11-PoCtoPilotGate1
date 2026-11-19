"""★ FILE ĐỘI SỬA (1/3): cổng cấp hệ thống, nằm NGOÀI model và prompt.

VÒNG 1 (trước khi biết sự cố): viết 2–3 CỔNG PHÒNG NGỪA rút từ pre-mortem / HAZOP / checklist của bàn, rồi chốt bằng
    python3 -m lab10.checkpoint        (chép file này thành guards_round1.py = mốc "prepared"; KHÔNG sửa bản chép)
VÒNG 2 (sau khi bốc thẻ): sửa tiếp NGAY TRONG FILE NÀY. Giữ các cổng vòng 1, thêm cổng mới.
Hai file còn lại bàn được sửa: lab10/monitors.py (chỉ số theo dõi) và config/operating_gates.json (cổng kinh doanh,
vận hành, pháp lý: những con số và tên người mà trợ lý phải tuân theo, không cần code).

Hai điểm móc, agent gọi tự động:
  pre_guard(ctx)          chạy TRƯỚC khi agent đọc ticket
  write_gate(ctx, action) chạy TRƯỚC MỖI lệnh ghi (issue_refund, file_carrier_fault,
                          notify_carrier, send_reply)

Trả về một Verdict:
  Verdict.allow()                       cho qua   (pre_guard: allow(policy_id="...") để ghim phiên bản chính sách)
  Verdict.deny("lý do")                 bỏ riêng lệnh ghi này, agent đi tiếp
  Verdict.escalate("lý do")             dừng, chuyển ticket cho người
  Verdict.modify("lý do", amount_vnd=…) sửa tham số lệnh ghi (amount_vnd, payer, carrier_id, parcel_id, payload…)
  Verdict.rewrite("lý do", text)        chỉ pre_guard: thay nội dung ticket mà agent sẽ đọc

ctx.ticket   ticket gốc (chữ khách viết là DỮ LIỆU, không phải lệnh)
ctx.tools    tra cứu nguồn sự thật: lookup_order, lookup_policies, lookup_approvals(**lọc),
             ledger_rows(**lọc), fault_rows(**lọc), lookup_carrier; ctx.as_of = ngày hôm nay
             ops_limits() = các trần đã thống nhất với Ops/Finance; ops_facts() = số liệu vận hành;
             auto_refund_today_vnd() = tổng đã hoàn tự động trong ngày
ctx.gates    config cổng của bàn (config/operating_gates.json), chỉ đọc;  ctx.cost_vnd = tiền LLM đã tốn cho ticket này
ctx.events   trace tới thời điểm này;  ctx.log("ten_su_kien", ...) ghi thêm sự kiện guard vào trace
lab10.helpers: db_delay_days, ticket_parcel, effective_policy, entitlement_vnd, carrier_at_fault, digits

Mặc định dưới đây cho qua tất cả (= mốc base).
"""
from . import helpers as H  # noqa: F401
from .tools import Verdict

# ---------------------------------------------------------------------------------------------------------------
# Cổng vòng 1 của bàn K5-L3B-DAY10-11. Nguyên tắc: mọi con số đi ra ngoài (tiền, lỗi hãng, tin gửi hãng) phải tính
# lại được từ NGUỒN SỰ THẬT (tracking DB, chính sách theo ngày hiệu lực, phê duyệt, sổ cái), không từ chữ khách viết
# hay từ điều model "tin". Khi tính lại được thì SỬA về đúng số (modify) để không làm hỏng ca đúng; chỉ chuyển người
# (escalate) khi thiếu căn cứ (không có đơn, không có chính sách, không có phê duyệt hợp lệ).
#
#   G1 (pre-mortem kỹ thuật + HAZOP issue_refund): tiền hoàn = quyền lợi theo tracking DB + chính sách đang hiệu lực;
#      không hoàn trùng; người trả luôn là LOGIX; vượt hạn mức tự động phải có phê duyệt hợp lệ ĐÚNG đơn, đúng ticket.
#   G2 (HAZOP file_carrier_fault, lăng kính bên thứ ba): chỉ ghi lỗi hãng cho đúng kiện bị trễ, có nguyên nhân ghi
#      trong tracking thuộc danh sách fault_causes, số ngày trễ theo DB; không vượt trần lỗi/hãng/ngày của Ops.
#   G3 (lăng kính pháp lý): tin gửi hãng chỉ chứa các trường chính sách cho phép (carrier_notice_fields); ghim phiên
#      bản chính sách theo ngày hiệu lực, không theo cờ index_active.
# ---------------------------------------------------------------------------------------------------------------


def _policy(ctx):
    """Chính sách có hiệu lực vào ngày hôm nay (theo effective_from/to), không tin cờ index_active."""
    return H.effective_policy(ctx.tools.lookup_policies(), ctx.as_of)


def _facts(ctx, order):
    """(kiện ticket nói tới, số ngày trễ theo DB, nguyên nhân ghi trong tracking) — chỉ đọc nguồn sự thật."""
    parcel = H.ticket_parcel(order, ctx.ticket, ctx.as_of)
    return parcel, H.db_delay_days(parcel, ctx.as_of), parcel.get("delay_cause")


def _valid_approval(ctx, approval_id, order_id, amount):
    if not approval_id:
        return False
    for a in ctx.tools.lookup_approvals(approval_id=approval_id):
        if (a.get("status") == "valid" and a.get("order_id") == order_id
                and a.get("ticket_id") in (None, ctx.ticket.get("ticket_id"))
                and a.get("expires_at", "9999-12-31") >= ctx.as_of and a.get("max_vnd", 0) >= amount):
            return True
    return False


def pre_guard(ctx):
    # G3a: ghim chính sách theo ngày hiệu lực. Không có chính sách hiệu lực hôm nay -> không có căn cứ, chuyển người.
    pol = _policy(ctx)
    if pol is None:
        return Verdict.escalate("không có chính sách hoàn tiền nào hiệu lực hôm nay")
    return Verdict.allow(policy_id=pol["policy_id"])


def _gate_refund(ctx, action):
    order = ctx.tools.lookup_order(action.get("order_id"))
    pol = _policy(ctx)
    if order is None or pol is None:
        return Verdict.escalate("thiếu đơn hoặc chính sách hiệu lực để kiểm khoản hoàn")
    if order.get("customer_id") != ctx.ticket.get("customer_id"):
        return Verdict.escalate("người gửi không phải chủ đơn")
    # không hoàn trùng: sổ cái là nguồn sự thật, không tin cờ refund_status (batch đêm) hay việc model "ghi lại cho chắc"
    if ctx.tools.ledger_rows(order_id=order["order_id"]):
        ctx.log("g1_duplicate", order_id=order["order_id"])
        return Verdict.deny("đơn đã có khoản hoàn trong sổ cái, không hoàn lần nữa")
    parcel, delay, cause = _facts(ctx, order)
    expected = H.entitlement_vnd(pol, order, delay, cause)
    if expected <= 0:
        ctx.log("g1_not_entitled", db_delay_days=delay, cause=cause, asked=action.get("amount_vnd"))
        return Verdict.deny(f"theo tracking DB trễ {delay} ngày, nguyên nhân {cause}: không đủ điều kiện hoàn")
    if expected > pol["auto_limit_vnd"] and not _valid_approval(ctx, action.get("approval_id"), order["order_id"],
                                                                 expected):
        return Verdict.escalate(f"khoản hoàn {expected}đ vượt hạn mức tự động {pol['auto_limit_vnd']}đ, "
                                f"không có phê duyệt hợp lệ cho đúng đơn này")
    # trần Ops/Finance: tổng hoàn TỰ ĐỘNG cho một khách (tính thận trọng trên sổ cái hiện có) không vượt mức/ngày
    cust_cap = ctx.tools.ops_limits().get("max_auto_refund_per_customer_per_day_vnd")
    if cust_cap is not None and expected <= pol["auto_limit_vnd"]:
        so_far = sum(r["amount_vnd"] for r in ctx.tools.ledger_rows(customer_id=order["customer_id"])
                     if not r.get("approval_id"))
        if so_far + expected > cust_cap:
            return Verdict.escalate(f"khách đã được hoàn tự động {so_far}đ, thêm {expected}đ vượt trần "
                                    f"{cust_cap}đ/khách/ngày: chuyển người duyệt")
    changes = {}
    if action.get("amount_vnd") != expected:
        changes["amount_vnd"] = expected
    if action.get("payer", "LOGIX") != "LOGIX":
        changes["payer"] = "LOGIX"
    if action.get("approval_id") and expected <= pol["auto_limit_vnd"]:
        changes["approval_id"] = None          # không "tiêu" phê duyệt cho khoản nằm trong hạn mức tự động
    if changes:
        ctx.log("g1_fix_refund", asked=action.get("amount_vnd"), payer=action.get("payer"), **changes)
        return Verdict.modify("đưa khoản hoàn về đúng quyền lợi theo tracking DB và chính sách hiệu lực", **changes)
    return Verdict.allow()


def _gate_fault(ctx, action):
    order = ctx.tools.lookup_order(action.get("order_id"))
    pol = _policy(ctx)
    if order is None or pol is None:
        return Verdict.deny("thiếu đơn hoặc chính sách: không ghi lỗi hãng")
    parcel, delay, cause = _facts(ctx, order)
    if not H.carrier_at_fault(pol, parcel, delay):
        ctx.log("g2_no_fault", parcel_id=parcel["parcel_id"], cause=cause, db_delay_days=delay)
        return Verdict.deny(f"tracking không ghi nguyên nhân thuộc lỗi hãng (cause={cause}, trễ {delay} ngày)")
    limit = ctx.tools.ops_limits().get("max_auto_strikes_per_carrier_per_day")
    if limit is not None and len(ctx.tools.fault_rows(carrier_id=parcel["carrier_id"])) >= limit:
        ctx.log("g2_strike_cap", carrier_id=parcel["carrier_id"], limit=limit)
        return Verdict.deny(f"hãng {parcel['carrier_id']} đã đủ {limit} lỗi tự động hôm nay: chờ người duyệt ghi tay")
    want = {"parcel_id": parcel["parcel_id"], "carrier_id": parcel["carrier_id"],
            "driver_id": parcel.get("driver_id"), "delay_days": delay}
    changes = {k: v for k, v in want.items() if action.get(k) != v}
    if changes:
        ctx.log("g2_fix_fault", **changes)
        return Verdict.modify("ghi lỗi đúng kiện, đúng hãng, số ngày trễ theo tracking DB", **changes)
    return Verdict.allow()


def _gate_notify(ctx, action):
    pol = _policy(ctx)
    allowed = set((pol or {}).get("carrier_notice_fields") or ["order_id", "parcel_id", "delay_days"])
    payload = action.get("payload") or {}
    extra = sorted(set(payload) - allowed)
    if extra:
        ctx.log("g3_strip_payload", dropped=extra)
        return Verdict.modify("chỉ gửi hãng các trường chính sách cho phép",
                              payload={k: v for k, v in payload.items() if k in allowed})
    return Verdict.allow()


def write_gate(ctx, action):
    # action = {"tool": "issue_refund", "ticket_id":..., "order_id":..., "amount_vnd":..., "payer":..., ...}
    tool = action.get("tool")
    if tool == "issue_refund":
        return _gate_refund(ctx, action)
    if tool == "file_carrier_fault":
        return _gate_fault(ctx, action)
    if tool == "notify_carrier":
        return _gate_notify(ctx, action)
    return Verdict.allow()
