import Swal from "sweetalert2";

// Base Dark Glassmorphism Theme for SweetAlert2
const darkSwal = Swal.mixin({
  background: "#121316",
  color: "#f4f4f5",
  backdrop: "rgba(0, 0, 0, 0.75)",
  customClass: {
    popup: "border border-zinc-700/80 rounded-2xl shadow-2xl font-sans p-5 backdrop-blur-md",
    title: "text-base font-semibold text-zinc-100 tracking-tight",
    htmlContainer: "text-xs text-zinc-400 leading-relaxed mt-2",
    confirmButton: "px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-md transition-all cursor-pointer mx-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50",
    cancelButton: "px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 rounded-lg text-xs font-medium transition-all cursor-pointer mx-1.5 focus:outline-none",
    input: "bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-indigo-500 placeholder-zinc-500 w-full mt-3 font-sans",
  },
  buttonsStyling: false,
});

export const alertSuccess = (title: string, text?: string) => {
  return darkSwal.fire({
    icon: "success",
    title,
    text,
    timer: 2500,
    timerProgressBar: true,
    showConfirmButton: false,
  });
};

export const alertError = (title: string, text?: string) => {
  return darkSwal.fire({
    icon: "error",
    title,
    text,
    confirmButtonText: "Đã hiểu",
  });
};

export const alertWarning = (title: string, text?: string) => {
  return darkSwal.fire({
    icon: "warning",
    title,
    text,
    confirmButtonText: "Đã hiểu",
  });
};

export const alertInfo = (title: string, text?: string) => {
  return darkSwal.fire({
    icon: "info",
    title,
    text,
    confirmButtonText: "Đóng",
  });
};

export const confirmDialog = async (options: {
  title: string;
  text?: string;
  confirmText?: string;
  cancelText?: string;
  isDestructive?: boolean;
}): Promise<boolean> => {
  const result = await darkSwal.fire({
    title: options.title,
    text: options.text,
    icon: options.isDestructive ? "warning" : "question",
    showCancelButton: true,
    confirmButtonText: options.confirmText || (options.isDestructive ? "Xóa" : "Xác nhận"),
    cancelButtonText: options.cancelText || "Hủy bỏ",
    reverseButtons: true,
    customClass: {
      popup: "border border-zinc-700/80 rounded-2xl shadow-2xl font-sans p-5 backdrop-blur-md",
      title: "text-base font-semibold text-zinc-100 tracking-tight",
      htmlContainer: "text-xs text-zinc-400 leading-relaxed mt-2",
      confirmButton: options.isDestructive
        ? "px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow-md transition-all cursor-pointer mx-1.5 focus:outline-none"
        : "px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-md transition-all cursor-pointer mx-1.5 focus:outline-none",
      cancelButton: "px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 rounded-lg text-xs font-medium transition-all cursor-pointer mx-1.5 focus:outline-none",
    },
  });
  return result.isConfirmed;
};

export const promptDialog = async (options: {
  title: string;
  text?: string;
  inputPlaceholder?: string;
  inputValue?: string;
  required?: boolean;
}): Promise<string | null> => {
  const result = await darkSwal.fire({
    title: options.title,
    text: options.text,
    input: "text",
    inputValue: options.inputValue || "",
    inputPlaceholder: options.inputPlaceholder || "",
    showCancelButton: true,
    confirmButtonText: "Xác nhận",
    cancelButtonText: "Hủy",
    reverseButtons: true,
    inputValidator: options.required !== false ? (value) => {
      if (!value || !value.trim()) {
        return "Vui lòng nhập thông tin!";
      }
      return null;
    } : undefined,
  });

  if (result.isConfirmed && result.value !== undefined) {
    return result.value.trim();
  }
  return null;
};

// Toast Notifications
const Toast = Swal.mixin({
  toast: true,
  position: "top-end",
  showConfirmButton: false,
  timer: 3000,
  timerProgressBar: true,
  background: "#18181b",
  color: "#f4f4f5",
  customClass: {
    popup: "border border-zinc-700/80 rounded-xl shadow-xl text-xs py-2.5 px-3 flex items-center font-sans",
    title: "text-xs font-medium text-zinc-200",
  },
  didOpen: (toast) => {
    toast.addEventListener("mouseenter", Swal.stopTimer);
    toast.addEventListener("mouseleave", Swal.resumeTimer);
  },
});

export const toastSuccess = (title: string) => {
  Toast.fire({
    icon: "success",
    title,
  });
};

export const toastError = (title: string) => {
  Toast.fire({
    icon: "error",
    title,
  });
};

export const toastInfo = (title: string) => {
  Toast.fire({
    icon: "info",
    title,
  });
};
