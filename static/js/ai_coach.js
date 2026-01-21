/**
 * AI Coach Frontend Module
 * ========================
 * Handles weight suggestions, deload/progression banners, and Adapt My Week modal.
 * 
 * Include this in your base template or specific pages that need coach features.
 */

const AICoach = {
    // Cache for weight suggestions
    suggestionCache: {},
    
    // Current recommendation (if any)
    currentRecommendation: null,
    
    /**
     * Initialize coach features on page load
     */
    init: function(options = {}) {
        this.cycleId = options.cycleId || null;
        this.onRecommendation = options.onRecommendation || null;
        
        // Check for recommendations on plan page
        if (options.checkRecommendations && this.cycleId) {
            this.checkForRecommendations();
        }
        
        // Check if adapt option should show
        if (options.checkAdaptOption && this.cycleId) {
            this.checkAdaptOption();
        }
    },
    
    // ==========================================
    // WEIGHT SUGGESTIONS
    // ==========================================
    
    /**
     * Get weight suggestion for a single exercise
     * @param {string} exerciseId - Exercise UUID
     * @param {object} options - {isHeavy, repLow, repHigh}
     * @returns {Promise<object>} Suggestion object
     */
    async getWeightSuggestion(exerciseId, options = {}) {
        // Check cache first
        const cacheKey = `${exerciseId}-${options.isHeavy}`;
        if (this.suggestionCache[cacheKey]) {
            return this.suggestionCache[cacheKey];
        }
        
        const params = new URLSearchParams({
            is_heavy: options.isHeavy !== false ? 'true' : 'false',
            rep_low: options.repLow || 6,
            rep_high: options.repHigh || 12
        });
        
        try {
            const response = await fetch(`/api/coach/weight-suggestion/${exerciseId}?${params}`);
            if (response.ok) {
                const data = await response.json();
                this.suggestionCache[cacheKey] = data;
                return data;
            }
        } catch (err) {
            console.error('Failed to get weight suggestion:', err);
        }
        
        return null;
    },
    
    /**
     * Get weight suggestions for all exercises in a workout
     * @param {array} exercises - Array of exercise objects with id, is_heavy, rep_range
     * @returns {Promise<object>} Map of exerciseId -> suggestion
     */
    async getWorkoutSuggestions(exercises) {
        try {
            const response = await fetch('/api/coach/workout-suggestions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ exercises })
            });
            
            if (response.ok) {
                const data = await response.json();
                // Update cache
                Object.assign(this.suggestionCache, data);
                return data;
            }
        } catch (err) {
            console.error('Failed to get workout suggestions:', err);
        }
        
        return {};
    },
    
    /**
     * Render a weight suggestion hint next to an input
     * @param {HTMLElement} inputElement - The weight input element
     * @param {object} suggestion - Suggestion object from API
     */
    renderSuggestionHint(inputElement, suggestion) {
        // Remove existing hint if any
        const existingHint = inputElement.parentElement.querySelector('.weight-hint');
        if (existingHint) existingHint.remove();
        
        if (!suggestion || !suggestion.suggested_weight) return;
        
        const hint = document.createElement('button');
        hint.type = 'button';
        hint.className = 'weight-hint text-xs text-cyan-400 hover:text-cyan-300 ml-2 transition-colors';
        hint.innerHTML = `💡 ${suggestion.suggested_weight}`;
        hint.title = suggestion.explanation;
        
        // Click to apply suggestion
        hint.addEventListener('click', () => {
            inputElement.value = suggestion.suggested_weight;
            inputElement.dispatchEvent(new Event('change', { bubbles: true }));
            hint.classList.add('text-green-400');
            hint.innerHTML = `✓ ${suggestion.suggested_weight}`;
        });
        
        inputElement.parentElement.appendChild(hint);
    },
    
    // ==========================================
    // DELOAD/PROGRESSION RECOMMENDATIONS
    // ==========================================
    
    /**
     * Check for any pending recommendations
     */
    async checkForRecommendations() {
        if (!this.cycleId) return;
        
        try {
            const response = await fetch(`/api/coach/check?cycle_id=${this.cycleId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.has_recommendation) {
                    this.currentRecommendation = data.recommendation;
                    this.showRecommendationBanner(data.recommendation);
                    
                    if (this.onRecommendation) {
                        this.onRecommendation(data.recommendation);
                    }
                }
            }
        } catch (err) {
            console.error('Failed to check recommendations:', err);
        }
    },
    
    /**
     * Show recommendation banner in the UI
     * @param {object} recommendation - Recommendation object
     */
    showRecommendationBanner(recommendation) {
        const container = document.getElementById('coach-banner-container');
        if (!container) {
            console.warn('No #coach-banner-container found in DOM');
            return;
        }
        
        const prescription = recommendation.prescription || {};
        const isDeload = recommendation.type === 'deload';
        
        const bannerHTML = `
            <div id="coach-recommendation-banner" 
                 class="bg-gradient-to-r ${isDeload ? 'from-amber-900/50 to-orange-900/50 border-amber-600' : 'from-emerald-900/50 to-green-900/50 border-emerald-600'} 
                        border rounded-lg p-4 mb-4 animate-fade-in">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-2 mb-2">
                            <span class="text-xl">${isDeload ? '📉' : '📈'}</span>
                            <h3 class="font-semibold text-white">${prescription.title || 'Coach Recommendation'}</h3>
                        </div>
                        <p class="text-gray-300 text-sm mb-3">${prescription.explanation || ''}</p>
                        ${prescription.prescription ? `
                            <p class="text-white text-sm bg-black/30 rounded p-2 mb-3">
                                <strong>This week:</strong> ${prescription.prescription}
                            </p>
                        ` : ''}
                        ${prescription.motivation ? `
                            <p class="text-gray-400 text-xs italic">${prescription.motivation}</p>
                        ` : ''}
                    </div>
                    <button onclick="AICoach.dismissBanner()" 
                            class="text-gray-500 hover:text-gray-300 p-1">
                        ✕
                    </button>
                </div>
                <div class="flex gap-2 mt-3">
                    <button onclick="AICoach.applyRecommendation('${recommendation.id}')"
                            class="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm rounded-lg transition-colors">
                        ${isDeload ? 'Apply Deload' : 'Got It'}
                    </button>
                    <button onclick="AICoach.dismissRecommendation('${recommendation.id}')"
                            class="px-4 py-2 bg-dark-600 hover:bg-dark-500 text-gray-300 text-sm rounded-lg transition-colors">
                        Remind Me Later
                    </button>
                </div>
            </div>
        `;
        
        container.innerHTML = bannerHTML;
    },
    
    /**
     * Apply a recommendation
     */
    async applyRecommendation(recommendationId) {
        try {
            const response = await fetch(`/api/coach/recommendation/${recommendationId}/apply`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.dismissBanner();
                this.showToast('Recommendation applied! 💪', 'success');
            }
        } catch (err) {
            console.error('Failed to apply recommendation:', err);
        }
    },
    
    /**
     * Dismiss a recommendation
     */
    async dismissRecommendation(recommendationId) {
        try {
            await fetch(`/api/coach/recommendation/${recommendationId}/dismiss`, {
                method: 'POST'
            });
            this.dismissBanner();
        } catch (err) {
            console.error('Failed to dismiss recommendation:', err);
        }
    },
    
    /**
     * Remove the banner from DOM
     */
    dismissBanner() {
        const banner = document.getElementById('coach-recommendation-banner');
        if (banner) {
            banner.classList.add('animate-fade-out');
            setTimeout(() => banner.remove(), 300);
        }
    },
    
    // ==========================================
    // ADAPT MY WEEK
    // ==========================================
    
    /**
     * Check if adapt option should be shown
     */
    async checkAdaptOption() {
        if (!this.cycleId) return;
        
        try {
            const response = await fetch(`/api/coach/adapt-check?cycle_id=${this.cycleId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.show_option) {
                    this.showAdaptButton(data.reason);
                }
            }
        } catch (err) {
            console.error('Failed to check adapt option:', err);
        }
    },
    
    /**
     * Show the "Adapt My Week" button
     */
    showAdaptButton(reason) {
        const container = document.getElementById('adapt-button-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="flex items-center gap-2 text-sm text-amber-400 mt-2">
                <span>⚡</span>
                <span>${reason}</span>
                <button onclick="AICoach.openAdaptModal()"
                        class="text-cyan-400 hover:text-cyan-300 underline ml-1">
                    Adapt My Week
                </button>
            </div>
        `;
    },
    
    /**
     * Open the adapt week modal
     */
    async openAdaptModal() {
        // Show loading state
        this.showModal(`
            <div class="text-center py-8">
                <div class="animate-spin w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                <p class="text-gray-400">Analyzing your week...</p>
            </div>
        `, 'Adapt Your Week');
        
        // Call API
        try {
            const response = await fetch('/api/coach/adapt-week', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cycle_id: this.cycleId,
                    request: 'Adapt my remaining week to be as effective as possible'
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.renderAdaptSuggestions(data);
            } else if (response.status === 429) {
                this.showModal(`
                    <div class="text-center py-8">
                        <p class="text-amber-400 mb-4">Daily AI limit reached</p>
                        <p class="text-gray-400 text-sm">Try again tomorrow, or plan your workout manually.</p>
                    </div>
                `, 'Adapt Your Week');
            } else {
                throw new Error('API error');
            }
        } catch (err) {
            console.error('Adapt week error:', err);
            this.showModal(`
                <div class="text-center py-8">
                    <p class="text-red-400 mb-4">Something went wrong</p>
                    <p class="text-gray-400 text-sm">Please try again later.</p>
                </div>
            `, 'Adapt Your Week');
        }
    },
    
    /**
     * Render adapt suggestions in modal
     */
    renderAdaptSuggestions(data) {
        const suggestions = data.suggestions || [];
        
        let suggestionsHTML = '';
        suggestions.forEach((suggestion, index) => {
            const exercisesList = (suggestion.exercises || [])
                .map(ex => `<li class="flex justify-between"><span>${ex.name}</span><span class="text-gray-500">${ex.sets}×${ex.reps}</span></li>`)
                .join('');
            
            suggestionsHTML += `
                <div class="bg-dark-700 rounded-lg p-4 mb-4 border border-dark-500 hover:border-cyan-600 transition-colors">
                    <div class="flex justify-between items-start mb-2">
                        <h4 class="font-semibold text-white">${suggestion.name}</h4>
                        <span class="text-xs text-gray-500">${suggestion.estimated_minutes || 45} min</span>
                    </div>
                    <p class="text-sm text-gray-400 mb-3">${suggestion.rationale}</p>
                    <ul class="text-sm space-y-1 text-gray-300 mb-3">
                        ${exercisesList}
                    </ul>
                    <div class="flex items-center justify-between">
                        <div class="flex gap-1 flex-wrap">
                            ${(suggestion.muscles_covered || []).map(m => 
                                `<span class="text-xs bg-dark-600 px-2 py-0.5 rounded">${m}</span>`
                            ).join('')}
                        </div>
                        <button onclick="AICoach.applySuggestion(${index}, ${JSON.stringify(suggestion).replace(/"/g, '&quot;')})"
                                class="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm rounded-lg transition-colors">
                            Apply
                        </button>
                    </div>
                </div>
            `;
        });
        
        const content = `
            <p class="text-gray-300 mb-4">${data.situation_summary || ''}</p>
            ${suggestionsHTML}
            ${data.tip ? `<p class="text-sm text-gray-500 italic mt-4">💡 ${data.tip}</p>` : ''}
        `;
        
        this.showModal(content, 'Adapt Your Week');
    },
    
    /**
     * Apply a suggestion from the adapt modal
     */
    async applySuggestion(index, suggestion) {
        // Get the next available date (today or tomorrow)
        const today = new Date();
        const scheduledDate = today.toISOString().split('T')[0];
        
        try {
            const response = await fetch('/api/coach/apply-adaptation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cycle_id: this.cycleId,
                    suggestion_index: index,
                    suggestion: suggestion,
                    scheduled_date: scheduledDate
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.closeModal();
                this.showToast(data.message, 'success');
                
                // Optionally reload the page to show new workout
                setTimeout(() => location.reload(), 1500);
            }
        } catch (err) {
            console.error('Apply suggestion error:', err);
            this.showToast('Failed to apply workout', 'error');
        }
    },
    
    // ==========================================
    // UI HELPERS
    // ==========================================
    
    /**
     * Show a modal dialog
     */
    showModal(content, title = '') {
        // Remove existing modal
        this.closeModal();
        
        const modal = document.createElement('div');
        modal.id = 'coach-modal';
        modal.className = 'fixed inset-0 z-50 flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-black/70" onclick="AICoach.closeModal()"></div>
            <div class="relative bg-dark-800 rounded-xl max-w-lg w-full max-h-[80vh] overflow-y-auto shadow-xl border border-dark-600 animate-fade-in">
                <div class="sticky top-0 bg-dark-800 px-6 py-4 border-b border-dark-600 flex justify-between items-center">
                    <h3 class="text-lg font-semibold text-white">${title}</h3>
                    <button onclick="AICoach.closeModal()" class="text-gray-500 hover:text-gray-300 text-xl">✕</button>
                </div>
                <div class="p-6">
                    ${content}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        document.body.classList.add('overflow-hidden');
    },
    
    /**
     * Close modal
     */
    closeModal() {
        const modal = document.getElementById('coach-modal');
        if (modal) {
            modal.remove();
            document.body.classList.remove('overflow-hidden');
        }
    },
    
    /**
     * Show a toast notification
     */
    showToast(message, type = 'info') {
        const colors = {
            success: 'bg-green-600',
            error: 'bg-red-600',
            info: 'bg-cyan-600'
        };
        
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 ${colors[type]} text-white px-4 py-3 rounded-lg shadow-lg z-50 animate-fade-in`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('animate-fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

// Add required CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeOut {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(-10px); }
    }
    .animate-fade-in { animation: fadeIn 0.3s ease-out; }
    .animate-fade-out { animation: fadeOut 0.3s ease-out forwards; }
`;
document.head.appendChild(style);

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AICoach;
}
