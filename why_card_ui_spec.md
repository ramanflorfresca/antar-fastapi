
# WHY CARD — UI Spec for Lovable / Ask Antar Chat
# ================================================
# 
# When the /predict response includes a 'why_this' field,
# display it as a distinct card ABOVE the plain_summary text.
#
# ┌──────────────────────────────────────────────┐
# │  ✦ Signal line (teal, bold)                  │
# ├──────────────────────────────────────────────┤
# │  WHY THIS IS HAPPENING                       │  ← 9px, uppercase, amber
# │  "At 57, you've entered a chapter that       │  ← 13px, italic, amber left border
# │   audits every business relationship..."     │
# ├──────────────────────────────────────────────┤
# │  Plain summary text here...                  │  ← 14px, normal
# │                                              │
# │  [HIGH CONFIDENCE] [CAREER] [◎ timing]       │  ← badges
# │                                              │
# │  ┌──────────────────────────────────────┐    │
# │  │ YOUR MOVE                            │    │  ← teal card
# │  │ Action item text...                  │    │
# │  └──────────────────────────────────────┘    │
# └──────────────────────────────────────────────┘
#
# Design tokens:
#   WHY label:  fontSize: 9, fontWeight: 700, letterSpacing: 0.08em, 
#               textTransform: uppercase, color: T.amber
#   WHY text:   fontSize: 13, fontStyle: italic, color: T.text, 
#               lineHeight: 1.55, paddingLeft: 12,
#               borderLeft: 2px solid T.amber
#   WHY card:   marginBottom: 10, padding: 10px 12px, borderRadius: 10,
#               background: T.amber + "06", border: 1px solid T.amber + "12"
#
# Conditional: Only show WHY card if why_this is present and non-empty.
# Animation: Fade in 200ms before plain_summary (stagger).
#
# React pseudo-code:
#
#   {msg.meta?.why_this && (
#     <div style={{
#       padding: "10px 12px", borderRadius: 10, marginBottom: 10,
#       background: T.amber + "06", border: `1px solid ${T.amber}12`,
#     }}>
#       <div style={{
#         fontSize: 9, fontWeight: 700, letterSpacing: "0.08em",
#         textTransform: "uppercase", color: T.amber, marginBottom: 4,
#       }}>
#         WHY THIS IS HAPPENING
#       </div>
#       <div style={{
#         fontSize: 13, fontStyle: "italic", color: T.text,
#         lineHeight: 1.55, paddingLeft: 12,
#         borderLeft: `2px solid ${T.amber}`,
#       }}>
#         {msg.meta.why_this}
#       </div>
#     </div>
#   )}
#
# Frontend field mapping from /predict response:
#   msg.meta.why_this    = response.why_this     (NEW)
#   msg.text             = response.plain_summary
#   msg.meta.confidence  = response.signal_confidence
#   msg.meta.timing      = response.timing_window
#   msg.meta.action      = response.action_item
#   msg.meta.signal      = response.signal_line
#   msg.meta.domains     = response.all_domains
