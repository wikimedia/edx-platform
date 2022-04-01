import React from 'react';

export default function Spinner({center_in_screen}) {
    return (
        <div className={`spinner ${center_in_screen ? 'center-in-screen': ''}`}>
            <div className="spinner-item"></div>
            <div className="spinner-item"></div>
            <div className="spinner-item"></div>
            <div className="spinner-item"></div>
            <div className="spinner-item"></div>
        </div>
    );
}
