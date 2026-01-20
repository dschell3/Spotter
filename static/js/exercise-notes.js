/**
 * Exercise Notes Module
 * Handles viewing and editing personal notes on exercises during workouts
 */

const ExerciseNotes = {
    // Cache of notes loaded for current workout
    notesCache: {},
    
    // Current exercise being edited
    currentExerciseId: null,
    currentExerciseName: null,
    
    // Max note length
    MAX_LENGTH: 500,
    
    /**
     * Initialize notes for a workout by loading all notes in bulk
     * @param {Array} exerciseIds - Array of exercise UUIDs
     */
    async loadNotesForWorkout(exerciseIds) {
        if (!exerciseIds || exerciseIds.length === 0) return;
        
        try {
            const response = await fetch('/api/exercises/notes/bulk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ exercise_ids: exerciseIds })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.notesCache = data.notes || {};
                this.updateNoteIcons();
            }
        } catch (error) {
            console.error('Failed to load exercise notes:', error);
        }
    },
    
    /**
     * Update all note icons based on cached notes
     */
    updateNoteIcons() {
        document.querySelectorAll('.note-icon-btn').forEach(btn => {
            const exerciseId = btn.dataset.exerciseId;
            if (exerciseId) {
                const hasNote = !!this.notesCache[exerciseId];
                this.setIconState(btn, hasNote);
            }
        });
    },
    
    /**
     * Set the visual state of a note icon button
     * @param {Element} btn - The button element containing the icons
     * @param {boolean} hasNote - Whether a note exists
     */
    setIconState(btn, hasNote) {
        const emptyIcon = btn.querySelector('.note-icon-empty');
        const filledIcon = btn.querySelector('.note-icon-filled');
        
        if (hasNote) {
            if (emptyIcon) emptyIcon.classList.add('hidden');
            if (filledIcon) filledIcon.classList.remove('hidden');
        } else {
            if (emptyIcon) emptyIcon.classList.remove('hidden');
            if (filledIcon) filledIcon.classList.add('hidden');
        }
    },
    
    /**
     * Open the note modal for an exercise
     * @param {string} exerciseId - Exercise UUID
     * @param {string} exerciseName - Exercise name for display
     */
    openModal(exerciseId, exerciseName) {
        const modal = document.getElementById('notes-modal');
        const titleEl = document.getElementById('notes-modal-title');
        const textareaEl = document.getElementById('notes-textarea');
        const charCountEl = document.getElementById('notes-char-count');
        
        if (!modal || !textareaEl) {
            console.error('Note modal elements not found');
            return;
        }
        
        // Set current exercise
        this.currentExerciseId = exerciseId;
        this.currentExerciseName = exerciseName;
        
        // Set title
        if (titleEl) {
            titleEl.textContent = `Notes: ${exerciseName}`;
        }
        
        // Load existing note
        const existingNote = this.notesCache[exerciseId] || '';
        textareaEl.value = existingNote;
        
        // Update character count
        this.updateCharCount(existingNote.length);
        
        // Show modal
        modal.classList.remove('hidden');
        textareaEl.focus();
    },
    
    /**
     * Close the note modal
     */
    closeModal() {
        const modal = document.getElementById('notes-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
        this.currentExerciseId = null;
        this.currentExerciseName = null;
    },
    
    /**
     * Update character count display
     */
    updateCharCount(length) {
        const charCountEl = document.getElementById('notes-char-count');
        if (charCountEl) {
            charCountEl.textContent = `${length}/${this.MAX_LENGTH}`;
        }
    },
    
    /**
     * Save the current note
     */
    async saveNote() {
        const textareaEl = document.getElementById('notes-textarea');
        const exerciseId = this.currentExerciseId;
        const noteText = textareaEl?.value?.trim() || '';
        
        if (!exerciseId) {
            console.error('No exercise ID set');
            return;
        }
        
        try {
            const response = await fetch(`/api/exercises/${exerciseId}/note`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ note_text: noteText })
            });
            
            if (response.ok) {
                // Update cache
                if (noteText) {
                    this.notesCache[exerciseId] = noteText;
                } else {
                    delete this.notesCache[exerciseId];
                }
                
                // Update icon
                const btn = document.querySelector(`.note-icon-btn[data-exercise-id="${exerciseId}"]`);
                if (btn) {
                    this.setIconState(btn, !!noteText);
                }
                
                // Close modal
                this.closeModal();
                
                // Show brief feedback
                this.showToast(noteText ? 'Note saved' : 'Note deleted');
            } else {
                const data = await response.json();
                alert(data.error || 'Failed to save note');
            }
        } catch (error) {
            console.error('Failed to save note:', error);
            alert('Failed to save note. Please try again.');
        }
    },
    
    /**
     * Delete the current note
     */
    async deleteNote() {
        const textareaEl = document.getElementById('notes-textarea');
        if (textareaEl) {
            textareaEl.value = '';
        }
        this.updateCharCount(0);
        await this.saveNote();
    },
    
    /**
     * Show a brief toast notification
     */
    showToast(message) {
        // Check if toast container exists, if not create it
        let toast = document.getElementById('notes-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'notes-toast';
            toast.className = 'fixed bottom-24 left-1/2 -translate-x-1/2 px-4 py-2 bg-dark-700 text-gray-200 text-sm rounded-lg shadow-lg transition-opacity duration-300 opacity-0 pointer-events-none z-50';
            document.body.appendChild(toast);
        }
        
        toast.textContent = message;
        toast.classList.remove('opacity-0');
        toast.classList.add('opacity-100');
        
        setTimeout(() => {
            toast.classList.remove('opacity-100');
            toast.classList.add('opacity-0');
        }, 2000);
    }
};

// Initialize event listeners when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Set up textarea character count listener
    const textarea = document.getElementById('notes-textarea');
    if (textarea) {
        textarea.addEventListener('input', function() {
            ExerciseNotes.updateCharCount(this.value.length);
            
            // Enforce max length
            if (this.value.length > ExerciseNotes.MAX_LENGTH) {
                this.value = this.value.substring(0, ExerciseNotes.MAX_LENGTH);
                ExerciseNotes.updateCharCount(ExerciseNotes.MAX_LENGTH);
            }
        });
    }
    
    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            ExerciseNotes.closeModal();
        }
    });
});
