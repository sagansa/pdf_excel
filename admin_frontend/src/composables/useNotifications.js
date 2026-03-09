import { reactive, readonly } from 'vue';

const notifications = reactive([]);
let notificationSeed = 0;

const normalizeTimeout = (value, fallback = 3200) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

const removeNotification = (id) => {
  const index = notifications.findIndex((item) => item.id === id);
  if (index >= 0) {
    notifications.splice(index, 1);
  }
};

const pushNotification = (payload = {}) => {
  const id = `notif-${Date.now()}-${notificationSeed += 1}`;
  const duration = normalizeTimeout(payload.duration);

  notifications.push({
    id,
    title: payload.title || '',
    message: payload.message || '',
    type: payload.type || 'info',
    duration,
  });

  if (duration > 0) {
    window.setTimeout(() => removeNotification(id), duration);
  }

  return id;
};

export const useNotifications = () => ({
  notifications: readonly(notifications),
  notify: pushNotification,
  success(message, options = {}) {
    return pushNotification({
      type: 'success',
      title: options.title || 'Berhasil',
      message,
      duration: options.duration,
    });
  },
  error(message, options = {}) {
    return pushNotification({
      type: 'error',
      title: options.title || 'Gagal',
      message,
      duration: options.duration || 4200,
    });
  },
  info(message, options = {}) {
    return pushNotification({
      type: 'info',
      title: options.title || 'Informasi',
      message,
      duration: options.duration,
    });
  },
  remove: removeNotification,
});
