// API 调用封装

const API = {
    baseUrl: '/api',

    // 获取笔记列表
    async getNotes(params = {}) {
        const query = new URLSearchParams();
        if (params.keyword) query.append('keyword', params.keyword);
        if (params.search) query.append('search', params.search);
        if (params.offset) query.append('offset', params.offset);
        if (params.limit) query.append('limit', params.limit);

        const response = await fetch(`${this.baseUrl}/notes?${query}`);
        if (!response.ok) throw new Error('Failed to fetch notes');
        return response.json();
    },

    // 获取笔记统计
    async getStats() {
        const response = await fetch(`${this.baseUrl}/notes/stats`);
        if (!response.ok) throw new Error('Failed to fetch stats');
        return response.json();
    },

    // 获取笔记详情
    async getNoteDetail(noteId) {
        const response = await fetch(`${this.baseUrl}/notes/${noteId}`);
        if (!response.ok) throw new Error('Failed to fetch note detail');
        return response.json();
    },

    // 获取关键词列表
    async getKeywords() {
        const response = await fetch(`${this.baseUrl}/notes/keywords`);
        if (!response.ok) throw new Error('Failed to fetch keywords');
        return response.json();
    },

    // 获取爬虫状态
    async getCrawlerStatus() {
        const response = await fetch(`${this.baseUrl}/crawler/status`);
        if (!response.ok) throw new Error('Failed to fetch crawler status');
        return response.json();
    }
};
