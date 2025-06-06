function init() {
  chrome.storage.local.get(
    { apiUrl: "", password: "" },
    (items) => {
      if(items.apiUrl == "" || items.password == ""){
        if (chrome.runtime.openOptionsPage) {
          chrome.runtime.openOptionsPage();
        } else {
          window.open(chrome.runtime.getURL('options.html'));
        }
      }
    }
  );

  getVideoInfo().then(videoInfo => {
    document.videoId = videoInfo.videoId;
    document.getElementById('title').value = videoInfo.channel + " - " + videoInfo.title;
  })

  exportCookies("youtube.com").then(cookies => {document.exportCookies = cookies;})
}

function add_download_link(data, response_data) {
    const downloadsContainer = document.getElementById('downloads');

    const linkWrapper = document.createElement('div');
    linkWrapper.className = 'download-item';

    const link = document.createElement('a');
    link.href = response_data.download_url;
    link.textContent = data.output_filename;

    // Create the delete button (red X)
    const deleteButton = document.createElement('span');
    deleteButton.className = 'delete';
    deleteButton.textContent = 'X';
    deleteButton.title = 'Remove this download';

    // Add event listener to the delete button
    deleteButton.addEventListener('click', function() {
        linkWrapper.remove(); // Remove the parent div when X is clicked
    });

    // Assemble the elements
    linkWrapper.appendChild(link);
    linkWrapper.appendChild(deleteButton);
    downloadsContainer.appendChild(linkWrapper);
}

function status(text, clear = false) {
  const status = document.getElementById('status');
  status.textContent = text;
  if(clear){
    setTimeout(() => {
      status.textContent = '';
    }, 5000);
  }
}

async function download() {
  status("Exporting...")
  var title = document.getElementById('title').value;
  var path = document.getElementById('path').value;

  const config_p = new Promise((resolve) => {
    chrome.storage.local.get(['apiUrl', 'password'], (result) => {
      resolve(result);
    });
  });
  const config = await config_p;

  const apiUrl = config.apiUrl;
  const password = config.password;
  const user = config.user;

  const data = {
    video_url: document.videoId,
    output_filename: title,
    path: path,
    cookies: document.exportCookies
  }

  makePutRequestWithBasicAuth(apiUrl, user, password, data)
  .then(response_data => {
    status('Success!', true);
    add_download_link(data, response_data);
  })
  .catch(error => status('Error: ' + JSON.stringify(error)));
}


document.addEventListener('DOMContentLoaded', init);
document.getElementById('cloud-ytdl').addEventListener('click', download);


async function exportCookies(domainFilter) {
  try {
    // Get cookies based on filter
    const cookies = await chrome.cookies.getAll({
      domain: domainFilter
    });
    
    if (cookies.length === 0) {
      alert('No cookies found' + (domainFilter ? ' for ' + domainFilter : '') + 
            '. Make sure you are logged in to YouTube.');
      return;
    }
    
    // Format as Netscape cookie file
    let output = "# Netscape HTTP Cookie File\n";
    output += "# https://curl.se/docs/http-cookies.html\n";
    output += "# This file was generated by Cloud YTDL extension.\n";
    output += "# It can be used by youtube-dl, yt-dlp and similar tools.\n\n";

    var count = 0;
    
    cookies.forEach(cookie => {
      count += 1;
      const secure = cookie.secure ? "TRUE" : "FALSE";
      // Convert expiration date to UNIX timestamp or use a default far future date
      const expiry = cookie.expirationDate ? 
                     Math.floor(cookie.expirationDate) : 
                     Math.floor(Date.now()/1000 + 365*24*60*60); // 1 year in future
      
      output += `${cookie.domain.startsWith('.') ? cookie.domain : '.' + cookie.domain}\t`;
      output += `TRUE\t`; // Always use TRUE for domain flag to ensure compatibility
      output += `${cookie.path}\t`;
      output += `${secure}\t`;
      output += `${expiry}\t`;
      output += `${cookie.name}\t`;
      output += `${cookie.value}\n`;
    });

    return output;
    
  } catch (error) {
    alert('Error getting cookies: ' + error.message);
    console.error(error);
  }
}

async function getVideoInfo() {
  // Get the current active tab
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});

  // Execute script in that tab
  const results = await chrome.scripting.executeScript({
    target: {tabId: tab.id},
    func: () => {
      url = new URL(document.URL);
      // This function runs in the context of the web page
      var channel = document.getElementById('channel-name').querySelector("#text").title;
      var videoId = url.searchParams.get("v");
      var title = document.title;

      if (title.endsWith(' - YouTube')) {
        title = title.slice(0, -10);
      }
      title = title.replace(/^\([^)]*\) /,"");

      return {
        url: url.toString(),
        channel: channel,
        videoId: videoId,
        title: title
      };
    }
  });

  // Results is an array of execution results
  return results[0].result;
}

async function makePutRequestWithBasicAuth(url, username, password, data) {
  try {
    // Create the Authorization header by encoding username:password in base64
    const credentials = btoa(`${username}:${password}`);
    
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Basic ${credentials}`
      },
      body: JSON.stringify(data)
    });

    const responseClone = response.clone()
    
    if (!response.ok) {

      responseClone.text().then(text => {
        console.error(`Error Text: $${text}`)
      })
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    return await response.json(); // Parse JSON response
  } catch (error) {
    console.error('Error making PUT request:', error);
    throw error;
  }
}

