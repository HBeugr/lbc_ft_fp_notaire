<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite">
      <TransitionGroup name="toast">
        <div
          v-for="toast in notifications.toasts"
          :key="toast.id"
          class="toast"
          :class="`toast--${toast.type}`"
          role="alert"
        >
          <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          <span class="toast-msg">{{ toast.message }}</span>
          <button class="toast-close" aria-label="Fermer" @click="notifications.removeToast(toast.id)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useNotificationsStore } from '@/stores/notifications'
const notifications = useNotificationsStore()
</script>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  max-width: 420px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 0.625rem;
  padding: 0.875rem 1rem;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.18);
  font-size: 0.8125rem;
  line-height: 1.5;
  pointer-events: all;
}

.toast--warning {
  background: #fffbeb;
  border: 1px solid #f59e0b;
  color: #78350f;
}

.toast--info {
  background: #eff6ff;
  border: 1px solid #3b82f6;
  color: #1e3a8a;
}

.toast--success {
  background: #f0fdf4;
  border: 1px solid #22c55e;
  color: #14532d;
}

.toast-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  margin-top: 1px;
  stroke: #f59e0b;
}

.toast--info .toast-icon    { stroke: #3b82f6; }
.toast--success .toast-icon { stroke: #22c55e; }

.toast-msg {
  flex: 1;
}

.toast-close {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  color: inherit;
  opacity: 0.55;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  margin-top: 1px;
}

.toast-close:hover { opacity: 1; }
.toast-close svg { width: 14px; height: 14px; }

/* Transitions */
.toast-enter-active { transition: all 0.25s ease; }
.toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from   { opacity: 0; transform: translateY(12px); }
.toast-leave-to     { opacity: 0; transform: translateX(20px); }
</style>
