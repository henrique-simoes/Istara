/**
 * Relay state machine.
 * States: connecting → idle → donating → user_active → disconnected
 */

const VALID_TRANSITIONS = {
  connecting: ["idle", "disconnected"],
  idle: ["donating", "user_active", "disconnected"],
  donating: ["idle", "user_active", "disconnected"],
  user_active: ["idle", "disconnected"],
  disconnected: ["connecting", "idle"],
};

export class StateMachine {
  constructor() {
    this.state = "connecting";
    this.listeners = [];
  }

  transition(newState) {
    const allowed = VALID_TRANSITIONS[this.state] || [];
    if (!allowed.includes(newState)) {
      console.warn(`⚠️ Invalid transition: ${this.state} → ${newState}`);
      return false;
    }
    const prev = this.state;
    this.state = newState;
    for (const fn of this.listeners) {
      try { fn(newState, prev); } catch {}
    }
    return true;
  }

  onTransition(fn) {
    this.listeners.push(fn);
  }
}
