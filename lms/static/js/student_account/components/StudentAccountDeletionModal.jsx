/* globals gettext */
/* eslint-disable react/no-danger */
import React from 'react';
import PropTypes from 'prop-types';
import { Button, Modal, Icon, InputText, StatusAlert } from '@edx/paragon/static';
import StringUtils from 'edx-ui-toolkit/js/utils/string-utils';

import { deactivate } from '../AccountsClient';
import removeLoggedInCookies from './removeLoggedInCookies';

class StudentAccountDeletionConfirmationModal extends React.Component {
  constructor(props) {
    super(props);

    this.deleteAccount = this.deleteAccount.bind(this);
    this.handleConfirmationInputChange = this.handleConfirmationInputChange.bind(this);
    this.confirmationFieldValidation = this.confirmationFieldValidation.bind(this);
    this.handleConfirmationModalClose = this.handleConfirmationModalClose.bind(this);
    
    // The text user needs to type to confirm deletion
    // TODO: This should be stored in a config file
    this.confirmationText = 'DELETE_MY_ACCOUNT';
    
    this.state = {
      confirmationInput: '',
      confirmationSubmitted: false,
      confirmationValid: true,
      validationMessage: '',
      validationErrorDetails: '',
      accountQueuedForDeletion: false,
      responseError: false,
    };
  }

  handleConfirmationModalClose() {
    this.props.onClose();

    removeLoggedInCookies();
    window.location.href = this.props.mktgRootLink;
  }

  deleteAccount() {
    return this.setState(
      { confirmationSubmitted: true },
      () => (
        deactivate()
          .then(() => this.setState({
            accountQueuedForDeletion: true,
            responseError: false,
            confirmationSubmitted: false,
            validationMessage: '',
            validationErrorDetails: '',
          }))
          .catch(error => this.failedSubmission(error))
      ),
    );
  }

  failedSubmission(error) {
    const title = gettext('Unable to delete account');
    const body = gettext('Sorry, there was an error trying to process your request. Please try again later.');

    this.setState({
      confirmationSubmitted: false,
      responseError: true,
      confirmationValid: false,
      validationMessage: title,
      validationErrorDetails: body,
    });
  }

  handleConfirmationInputChange(value) {
    this.setState({ confirmationInput: value });
    this.confirmationFieldValidation(value);
  }

  confirmationFieldValidation(value) {
    let feedback = { confirmationValid: true };

    if (value.length < 1) {
      feedback = {
        confirmationValid: false,
        validationMessage: gettext('Confirmation text is required'),
        validationErrorDetails: '',
      };
    } else if (value !== this.confirmationText) {
      feedback = {
        confirmationValid: false,
        validationMessage: gettext('Confirmation text does not match'),
        validationErrorDetails: StringUtils.interpolate(
          gettext('Please type "{confirmationText}" exactly as shown.'),
          { confirmationText: this.confirmationText }
        ),
      };
    }

    this.setState(feedback);
  }

  renderConfirmationModal() {
    const {
      confirmationValid,
      confirmationInput,
      confirmationSubmitted,
      responseError,
      validationErrorDetails,
      validationMessage,
    } = this.state;
    const { onClose } = this.props;
    const loseAccessText = StringUtils.interpolate(
      gettext('You may also lose access to verified certificates and other program credentials like MicroMasters certificates. If you want to make a copy of these for your records before proceeding with deletion, follow the instructions for {htmlStart}printing or downloading a certificate{htmlEnd}.'),
      {
        htmlStart: '<a href="https://edx.readthedocs.io/projects/edx-guide-for-students/en/latest/SFD_certificates.html#printing-a-certificate" rel="noopener" target="_blank">',
        htmlEnd: '</a>',
      },
    );

    const noteDeletion = StringUtils.interpolate(
      gettext('You have selected “Delete my account.” Deletion of your account and personal data is permanent and cannot be undone. {platformName} will not be able to recover your account or the data that is deleted.'),
      {
        platformName: this.props.platformName,
      },
    );

    const bodyDeletion = StringUtils.interpolate(
      gettext('If you proceed, you will be unable to use this account to take courses on the {platformName} app, {siteName}, or any other site hosted by {platformName}.'),
      {
        platformName: this.props.platformName,
        siteName: this.props.siteName,
      },
    );

    const bodyDeletion2 = StringUtils.interpolate(
      gettext('This includes access to {siteName} from your employer’s or university’s system{additionalSiteSpecificDeletionText}.'),
      {
        siteName: this.props.siteName,
        additionalSiteSpecificDeletionText: this.props.additionalSiteSpecificDeletionText,
      },
    );

    const confirmationInstructions = StringUtils.interpolate(
      gettext('If you still wish to continue and delete your account, please type "{confirmationText}" in the box below:'),
      { confirmationText: this.confirmationText }
    );

    return (
      <div className="delete-confirmation-wrapper">
        <Modal
          title={gettext('Are you sure?')}
          renderHeaderCloseButton={false}
          onClose={onClose}
          aria-live="polite"
          open
          body={(
            <div>
              {responseError &&
                <StatusAlert
                  dialog={(
                    <div className="modal-alert">
                      <div className="icon-wrapper">
                        <Icon id="delete-confirmation-body-error-icon" className={['fa', 'fa-exclamation-circle']} />
                      </div>
                      <div className="alert-content">
                        <h3 className="alert-title">{ validationMessage }</h3>
                        <p>{ validationErrorDetails }</p>
                      </div>
                    </div>
                  )}
                  alertType="danger"
                  dismissible={false}
                  open
                />
              }

              <StatusAlert
                dialog={(
                  <div className="modal-alert">
                    <div className="icon-wrapper">
                      <Icon id="delete-confirmation-body-warning-icon" className={['fa', 'fa-exclamation-triangle']} />
                    </div>
                    <div className="alert-content">
                      <h3 className="alert-title">{noteDeletion}</h3>
                      <p>
                        <span>{bodyDeletion} </span>
                        <span>{bodyDeletion2}</span>
                      </p>
                      <p dangerouslySetInnerHTML={{ __html: loseAccessText }} />
                    </div>
                  </div>
                )}
                dismissible={false}
                open
              />
              <p className="next-steps">{ confirmationInstructions }</p>
              <InputText
                name="confirm-deletion"
                type="text"
                className={['confirm-deletion-input']}
                onBlur={this.confirmationFieldValidation}
                isValid={confirmationValid}
                validationMessage={validationMessage}
                onChange={this.handleConfirmationInputChange}
                autoComplete="off"
                themes={['danger']}
                placeholder={gettext('Type confirmation text here')}
              />
            </div>
          )}
          closeText={gettext('Cancel')}
          buttons={[
            <Button
              label={gettext('Yes, Delete')}
              onClick={this.deleteAccount}
              disabled={confirmationInput.length === 0 || !confirmationValid || confirmationSubmitted}
            />,
          ]}
        />
      </div>
    );
  }

  renderSuccessModal() {
    return (
      <div className="delete-success-wrapper">
        <Modal
          title={gettext('We\'re sorry to see you go! Your account will be deleted shortly.')}
          renderHeaderCloseButton={false}
          body={gettext('Account deletion, including removal from email lists, may take a few weeks to fully process through our system. If you want to opt-out of emails before then, please unsubscribe from the footer of any email.')}
          onClose={this.handleConfirmationModalClose}
          aria-live="polite"
          open
        />
      </div>
    );
  }

  render() {
    const { accountQueuedForDeletion } = this.state;

    return accountQueuedForDeletion ? this.renderSuccessModal() : this.renderConfirmationModal();
  }
}

StudentAccountDeletionConfirmationModal.propTypes = {
  onClose: PropTypes.func,
  additionalSiteSpecificDeletionText: PropTypes.string,
  mktgRootLink: PropTypes.string,
  platformName: PropTypes.string,
  siteName: PropTypes.string,
};

StudentAccountDeletionConfirmationModal.defaultProps = {
  onClose: () => {},
  additionalSiteSpecificDeletionText: "",
  mktgRootLink: "",
  platformName: "",
  siteName: "",
};

export default StudentAccountDeletionConfirmationModal;
