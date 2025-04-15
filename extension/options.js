const defaultApiUrl = "https://03siej7whh.execute-api.us-east-2.amazonaws.com/prod/api";

// Saves options to chrome.storage
const saveOptions = () => {
  const apiUrl = document.getElementById('api-url').value;
  const password = document.getElementById('password').value;

  chrome.storage.local.set(
    { apiUrl: apiUrl, password: password, user: "admin" },
    () => {
      // Update status to let user know options were saved.
      const status = document.getElementById('status');
      status.textContent = 'Options saved.';
      setTimeout(() => {
        status.textContent = '';
      }, 750);
    }
  );
};

// Restores select box and checkbox state using the preferences
// stored in chrome.storage.
const restoreOptions = () => {
  console.log("getting pas")
  chrome.storage.local.get(
    { apiUrl: defaultApiUrl, password: "" },
    (items) => {
      document.getElementById('api-url').value = items.apiUrl;
      document.getElementById('password').value = items.password;
    }
  );
};

document.addEventListener('DOMContentLoaded', restoreOptions);
document.getElementById('save').addEventListener('click', saveOptions);
