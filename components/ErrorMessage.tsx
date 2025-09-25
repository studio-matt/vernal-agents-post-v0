'use client';

import React from 'react';

type ErrorMessageProps = {
    message?: string | string[] | null;
};

const ErrorMessage: React.FC<ErrorMessageProps> = ({ message }) => {
    if (!message || (Array.isArray(message) && message.length === 0)) return null;

    const messages = Array.isArray(message) ? message : [message];

    return (
        <div style={styles.container}>
            {messages.map((msg, idx) => (
                <p key={idx} style={styles.text}>{msg}</p>
            ))}
        </div>
    );
};

const styles: { [key: string]: React.CSSProperties } = {
    container: {
        padding: '12px',
        backgroundColor: '#ffe0e0',
        border: '1px solid #ff4d4f',
        borderRadius: '4px',
        color: '#a80000',
        marginTop: '1rem',
    },
    text: {
        margin: 0,
        fontWeight: 'bold',
    },
};

export default ErrorMessage;
