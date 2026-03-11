class StorageManager {
    save(key, data) {
        try {
            const json = JSON.stringify(data);
            localStorage.setItem(key, json);
        } catch (error) {
            console.error("Error saving data:", error);
        }
    }

    load(key) {
        try {
            const data = localStorage.getItem(key);
            if (!data) {
                return null;
            }
            return JSON.parse(data);
        } catch (error) {
            console.error("Error loading data:", error);
            return null;
        }
    }

    remove(key) {
        localStorage.removeItem(key);
    }

    clearAll() {
        localStorage.clear();
    }

    exportJSON(key, fileName = "data.json") {
        const data = this.load(key);
        if (!data) {
            console.warn("No data to export.");
            return;
        }
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }
}

const storage = new StorageManager();

document.getElementById('loadButton').addEventListener('click', async () => {
    const fileInput = document.getElementById('fileInput');
    const loadType = document.getElementById('loadType').value;
    const file = fileInput.files[0];
    if (!file) {
        alert('Please select a file.');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', loadType);

    try {
        const response = await fetch('/api/load-tree', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (response.ok) {
            storage.save('treeData', result);
            alert('Tree loaded and saved to LocalStorage.');
            // Here you can add code to visualize the tree
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        console.error('Error loading tree:', error);
    }
});

document.getElementById('saveButton').addEventListener('click', async () => {
    const treeData = storage.load('treeData');
    if (!treeData) {
        alert('No tree data in LocalStorage.');
        return;
    }

    try {
        const response = await fetch('/api/save-tree', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tree_type: 'avl',
                tree_data: treeData
            })
        });
        const result = await response.json();
        if (response.ok) {
            storage.exportJSON('treeData', 'tree.json');
            alert('Tree saved and exported.');
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        console.error('Error saving tree:', error);
    }
});